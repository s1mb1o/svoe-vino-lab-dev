"""Execute the page poll code. Verify bounded requests and failure recovery."""

from pathlib import Path
import shutil
import subprocess
import unittest


PAGE = Path(__file__).resolve().parents[1] / "pipeline/pages/embedding.html"


def block(source, start, end):
    first = source.index(start)
    last = source.index(end, first) + len(end)
    return source[first:last]


class EmbeddingPollingTest(unittest.TestCase):
    def test_slow_polls_share_requests_and_recover_after_a_failure(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required for the page behavior check")
        source = PAGE.read_text()
        definitions = "\n".join((
            block(source, "function singlePoll(refresh) {", "\n}"),
            block(source, "const runJobsStatus =", ";"),
            block(source, "const pollJobs = singlePoll(", "\n});"),
            block(source, "const pollSelftests = singlePoll(", "\n});"),
        ))
        setup = r'''
const assert = require("node:assert/strict");
const requests = [], displayed = [];
let SELFTESTS = {}, SELFTEST_POLL = null;
const SELFTEST_PREFIX = "selftest-", ACTIVE = ["running", "stopping"];
function getJson(url) {
  return new Promise((resolve, reject) => requests.push({url, resolve, reject}));
}
function setRuns(jobs) { displayed.push(["runs", jobs]); }
function showQueue(queue) { displayed.push(["queue", queue]); }
function showJobs(jobs) { displayed.push(["jobs", jobs]); }
function showSelftest() { displayed.push(["selftest", Object.keys(SELFTESTS)]); }
function setInterval() { return 1; }
function clearInterval() {}
'''
        checks = r'''
(async () => {
  const waiting = [];
  for (let index = 0; index < 20; index++) {
    waiting.push(pollJobs(), pollSelftests());
  }
  assert.equal(requests.length, 2, "forty polls must use two HTTP requests");
  assert.equal(requests.filter(item => item.url === "/api/run-jobs").length, 1);
  const jobs = [{name: "selftest-a", state: "running"}, {name: "pipeline-a", state: "running"}];
  requests.find(item => item.url === "/api/run-jobs").resolve({jobs});
  requests.find(item => item.url === "/api/embedding-jobs").resolve({jobs: [], queue: null});
  await Promise.all(waiting);
  assert.deepEqual(Object.keys(SELFTESTS), ["selftest-a"]);
  assert.equal(displayed.filter(item => item[0] === "jobs").length, 1);

  requests.length = 0;
  const failed = [pollJobs(), pollSelftests()];
  assert.equal(requests.length, 2, "completed requests must release their slots");
  for (const item of requests) item.reject(new Error("network failed"));
  await Promise.all(failed);

  requests.length = 0;
  const recovered = [pollJobs(), pollSelftests()];
  assert.equal(requests.length, 2, "failed requests must release their slots");
  for (const item of requests) item.resolve({jobs: [], queue: null});
  await Promise.all(recovered);
  assert.deepEqual(Object.keys(SELFTESTS), []);
  assert.equal(SELFTEST_POLL, null);
  console.log("Polling concurrency, shared status, and failure recovery pass.");
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
        result = subprocess.run([node, "-e", setup + definitions + checks],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
