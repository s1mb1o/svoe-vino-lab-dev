// Read-only access to the token owner's «Винный дневник» (issue #65).
// The token comes from CHTOZAVINO_ACCOUNT_TOKEN. It never appears in a result, an error, or stderr.

export const TOKEN_PATTERN = /^cvpat_[A-Za-z0-9_-]{43}$/;
export const DEFAULT_ACCOUNT_URL = 'https://chtozavino.ru';
const TIMEOUT_MS = 5000;
const MAX_RESPONSE_BYTES = 256 * 1024;
const LOOPBACK = new Set(['127.0.0.1', '[::1]', 'localhost']);

/** A start-up problem of the account settings. The message never contains the token. */
export class AccountConfigError extends Error {}

/** A failed account call: `unauthorized` for a refused token, `unavailable` for everything else. */
export class AccountToolError extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

/** Reads the body with a running byte count and stops past the limit, before it is all in memory. */
async function readLimited(response) {
  if (Number(response.headers.get('content-length') ?? 0) > MAX_RESPONSE_BYTES) throw new Error('too large');
  if (!response.body) return '';
  const reader = response.body.getReader();
  const chunks = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_RESPONSE_BYTES) {
      await reader.cancel();
      throw new Error('too large');
    }
    chunks.push(value);
  }
  return new TextDecoder().decode(Buffer.concat(chunks));
}

export class AccountClient {
  /** Returns null without a token: the server then works exactly as before. */
  static fromEnv(env = process.env, fetchImpl = globalThis.fetch) {
    const token = (env.CHTOZAVINO_ACCOUNT_TOKEN ?? '').trim();
    if (!token) return null;
    if (!TOKEN_PATTERN.test(token)) throw new AccountConfigError('CHTOZAVINO_ACCOUNT_TOKEN has a wrong format. Create a new token in «Винный дневник».');
    let base;
    try {
      base = new URL((env.CHTOZAVINO_ACCOUNT_URL ?? '').trim() || DEFAULT_ACCOUNT_URL);
    } catch {
      throw new AccountConfigError('CHTOZAVINO_ACCOUNT_URL is not a URL.');
    }
    const loopbackHttp = base.protocol === 'http:' && LOOPBACK.has(base.hostname);
    if ((base.protocol !== 'https:' && !loopbackHttp) || base.username || base.password || base.search || base.hash) {
      throw new AccountConfigError('CHTOZAVINO_ACCOUNT_URL must be an https URL without credentials, query, or fragment.');
    }
    return new AccountClient(token, base, fetchImpl);
  }

  #token;
  constructor(token, base, fetchImpl) {
    this.#token = token;
    this.origin = base.origin;
    this.host = base.host;
    this.fetch = fetchImpl;
  }

  async #get(path) {
    let response;
    try {
      response = await this.fetch(`${this.origin}${path}`, {
        headers: { Authorization: `Bearer ${this.#token}`, Accept: 'application/json' },
        redirect: 'error',
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
    } catch {
      throw new AccountToolError('unavailable', 'The diary service did not answer. Catalog tools still work.');
    }
    if (response.status === 401) throw new AccountToolError('unauthorized', 'The diary refused the account token. It may be revoked or expired. Create a new token in «Винный дневник».');
    if (response.status === 429) throw new AccountToolError('unavailable', 'Too many diary requests. Try again in a minute.');
    if (!response.ok) throw new AccountToolError('unavailable', 'The diary service is unavailable. Catalog tools still work.');
    try {
      return JSON.parse(await readLimited(response));
    } catch {
      throw new AccountToolError('unavailable', 'The diary service sent an unexpected answer.');
    }
  }

  profile() { return this.#get('/api/app/v1/profile'); }

  wines({ limit, cursor } = {}) {
    const params = new URLSearchParams();
    if (limit !== undefined) params.set('limit', String(limit));
    if (cursor) params.set('cursor', cursor);
    return this.#get(params.size ? `/api/app/v1/wines?${params}` : '/api/app/v1/wines');
  }
}
