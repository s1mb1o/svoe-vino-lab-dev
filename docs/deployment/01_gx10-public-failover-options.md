# GX10 public deployment and failover options

Date: 2026-09-28.
Status: proposal. No deployment change was made.

## Scope boundary

The public service MUST be the matcher API.
The lab server on port 8168 MUST stay private.
The lab server has no authentication.
The lab server writes to a local SQLite database.

The new `matcher/` service has upload limits, image validation, bounded concurrency,
Bearer authentication, and `GET /healthz`.
The current matcher backend is a mock backend.
It is not the production recognizer.
A production deployment requires the real matcher backend first.

## Required security property

The home router SHOULD have no new inbound port-forward rule.
The GX10 matcher SHOULD listen on loopback only.
The GX10 SHOULD make an outbound connection to a public edge.
The public edge MUST terminate TLS.
The public edge MUST expose only the required API route and health route.

## Option 1: public VPS edge with restricted reverse tunnels

This option is recommended for the current infrastructure.

Run Caddy on a small public VPS.
Run the matcher on GX10 at `127.0.0.1:8158`.
Create one outbound reverse SSH tunnel from GX10 to the VPS.
Create a second outbound reverse SSH tunnel from the backup server to the VPS.
Bind both forwarded ports to VPS loopback.
Caddy uses the GX10 tunnel as the first upstream.
Caddy uses the backup tunnel only when the GX10 tunnel is unhealthy.

Use this request path:

```text
Internet
  -> public VPS:443
  -> Caddy TLS, route filter, and health checks
  -> 127.0.0.1:18158 -> reverse SSH -> GX10 matcher
  -> 127.0.0.1:28158 -> reverse SSH -> backup matcher
```

The Caddy upstream order can implement active and standby routing:

```caddyfile
matcher.example.com {
    @public_api path /v1/eval/predict /healthz

    handle @public_api {
        reverse_proxy 127.0.0.1:18158 127.0.0.1:28158 {
            lb_policy first
            health_uri /healthz
            health_interval 10s
            health_timeout 3s
            health_fails 2
            health_passes 2
        }
    }

    respond 404
}
```

The example shows routing behavior only.
The final configuration MUST add access logs, retention, and rate limits.
The matcher MUST also enforce its own body, pixel, timeout, concurrency, and queue
limits.

Use a separate SSH account for each tunnel.
Disable shell and TTY access for each account.
Set `AllowTcpForwarding remote`.
Set `GatewayPorts no`.
Restrict each account with `PermitListen` to its one loopback port.
Use a dedicated key for each origin.
Run the tunnel with a systemd unit.
Set `ExitOnForwardFailure=yes` and SSH keepalives.

The edge VPS is a failure domain.
Use two edge providers or a managed global load balancer if edge failure must also be
covered.

### Fit with the present infrastructure

#### Selectel VDS size

Selectel VDS is suitable for the public edge.
The recommended fixed configuration is `VDS 1-2-25`:

- 1 vCPU;
- 2 GB RAM;
- 25 GB local disk;
- one public IPv4 address;
- Ubuntu 24.04 LTS or Debian 12;
- Moscow or Saint Petersburg.

The published price was 250 RUB per month on 2026-09-28.
The price includes 3 TB of external traffic and L3-L4 DDoS protection.
The smaller `VDS 1-1-10` configuration at 200 RUB per month is sufficient for Caddy
and two SSH tunnels.
The 2 GB and 25 GB configuration gives more space for system updates, logs, and
monitoring for 50 RUB more each month.

The edge needs no GPU.
The edge needs no Selectel managed load balancer.
Install Caddy and OpenSSH directly on the VDS.
Use the host firewall to allow TCP 80 and 443 from the Internet.
Allow the SSH port with key authentication only.
Selectel VDS does not provide security groups.

Saint Petersburg gives more geographic separation from the home site.
Moscow gives slightly lower latency for Moscow clients.
Select Saint Petersburg when failure-domain separation is more important than the
small latency difference.

The VDS has no automatic backup.
Keep the Caddy configuration and systemd units in Git.
Treat the VDS as replaceable infrastructure.
Do not store application data or matcher archives on it.

`alphavps-bg` has TCP port 443 available in the recorded configuration.
Its active AmneziaWG service uses UDP port 443.
It can support a proof of concept.
It has only 1 GB RAM and a nearly full small disk.
It also has an unrelated VPN role.
A separate small VPS gives a smaller blast radius.

`cloudzy-ams` already uses TCP port 443 for Xray.
It is not a simple Caddy edge without a service change.

`zelda` is preemptible and is currently frozen.
It is not a reliable warm standby.
It MAY be an on-demand compute fallback.

## Option 2: Cloudflare Tunnel and Cloudflare Load Balancing

Run one outbound `cloudflared` tunnel on GX10.
Run a separate tunnel on the backup server.
Create one origin pool for each tunnel.
Use failover steering with the GX10 pool first.
Attach an HTTPS health monitor.

Cloudflare Tunnel needs no inbound home port and no public home IP.
Cloudflare Load Balancing is an add-on feature.
This option reduces edge operations.
This option adds a Cloudflare dependency and can require a DNS change.

Multiple connectors with one tunnel UUID give connector redundancy.
They do not give ordered primary and standby origin pools.
Use separate tunnels and separate pools for ordered failover.

## Option 3: home MikroTik Caddy with a public route

This option has the smallest initial change.
The existing home Caddy already publishes selected GX10 services.
It keeps the public entry point inside the home failure domain.
It cannot send traffic to a backup when the home router, power, or ISP fails.
It also creates an inbound path into the home network.

Do not select this option for the requested failure boundary.
Use it only for a short demonstration after strict VLAN and firewall isolation.

## Backup server requirements

The backup MUST be outside the home power and ISP failure domains.
The backup MUST run the same immutable application release.
The backup MUST use the same catalogue and embedding index revision.
The backup readiness response SHOULD include the application revision and index digest.
The health monitor SHOULD reject a wrong revision or digest.

The backup MUST NOT call GX10 for SAM3, embeddings, VLM, or other required inference.
Such a dependency makes the backup fail with GX10.
The backup needs its own models or independent model services.

The matcher request archive is local state.
Each origin SHOULD write to a separate append-only path.
Each origin SHOULD copy archives to independent object storage.
Do not share an SQLite database between active origins.

## Runtime hardening

Run the matcher as a non-root user.
Use an immutable container image or a pinned virtual environment.
Mount configuration, catalogue data, models, and indexes read-only.
Mount one separate bounded output volume for request archives.
Keep secrets in a root-readable environment file or a systemd credential.
Do not put a token in YAML, Git, the container image, or a command line.

Enable automatic restart and start at boot.
Set CPU, memory, process, and file limits.
Drop Linux capabilities.
Set `no-new-privileges`.
Do not mount the Docker socket.

Publish only `/v1/eval/predict` and `/healthz`.
Return 404 for `/docs`, `/redoc`, `/openapi.json`, and all lab routes at the edge unless
they are required.
Keep Bearer authentication enabled in the matcher.
Use a different tunnel key and application token.

## Health and failover semantics

The current `matcher/healthz` response confirms that the process loaded its selected
pipeline.
It does not prove that a remote model dependency can answer.
A production readiness check MUST cover every required dependency.
A periodic synthetic prediction SHOULD verify the complete path.
Do not run an expensive model prediction every ten seconds.

Failover protects new requests after the primary becomes unhealthy.
One upload that is in progress during a failure can still fail.
The client SHOULD retry that request.
The service SHOULD accept an idempotency key if duplicate archive records are a problem.

## Recommended sequence

1. Integrate the real backend into the hardened matcher service.
2. Build one immutable ARM64 image for GX10.
3. Build the compatible backup image.
4. Pin the catalogue and index by digest.
5. Run both services on loopback.
6. Add dependency-aware readiness.
7. Create the outbound tunnels.
8. Configure the public edge and TLS.
9. Test token rejection, request limits, and route filtering.
10. Stop the GX10 matcher and measure automatic failover.
11. Restore GX10 and measure automatic failback.
12. Disconnect the home WAN and repeat the test.

## References

- Cloudflare Tunnel: <https://developers.cloudflare.com/tunnel/>
- Cloudflare Tunnel load balancing:
  <https://developers.cloudflare.com/tunnel/concepts/routing/#load-balancing>
- Cloudflare failover steering:
  <https://developers.cloudflare.com/load-balancing/understand-basics/traffic-steering/steering-policies/standard-options/>
- Caddy reverse proxy and health checks:
  <https://caddyserver.com/docs/caddyfile/directives/reverse_proxy>
- OpenSSH forwarding restrictions:
  <https://man.openbsd.org/sshd_config>
