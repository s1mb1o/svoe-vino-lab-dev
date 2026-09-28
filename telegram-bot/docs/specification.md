# Product specification

Date: 2026-09-26

## Purpose

The bot identifies a wine from one Telegram photo or from each photo in a Telegram album.
The bot returns the catalogue name and the page URL.
The service also collects difficult test images for recognition improvement.

## Production user flow

1. The user opens `@ChtoZaVinoBot`.
2. The bot shows the service purpose, the data notice, and the alcohol notice.
3. The bot asks the user to confirm that the user is at least 18 years old.
4. The user selects one age confirmation button.
5. The user sends one photo.
6. The bot checks the saved age confirmation.
7. The bot checks the user rate limit.
8. The bot adds the request to the processing queue.
9. A queue worker downloads and moderates the photo.
10. The bot rejects an unsafe photo.
11. A queue worker recognizes a safe photo.
12. The bot returns one name and one catalogue link.

## Functional requirements

1. The bot MUST use Telegram long polling.
2. The bot MUST accept Telegram photo messages.
3. The bot MUST limit one Telegram user ID to 50 image requests in a rolling hour.
4. The rate limit MUST survive a process restart.
5. `moderation.enabled` in `config.yaml` MUST control image moderation.
   The value MUST default to `true`.
   Production MUST refuse to start when it is `false`.
   Local development and tests MAY set it to `false`.
   The bot then MUST bypass ShieldGemma.
   The bot MUST record the moderation category as `disabled` and store no safety verdict.
6. An enabled moderation check MUST use the `dangerous`, `sexual`, and `violence` policies.
7. An enabled moderation error MUST stop the request before image storage and recognition.
8. The bot MUST store an image under `accepted` after safe moderation or an explicit
non-production moderation bypass.
9. The bot MUST store unsafe images under `quarantine`.
10. The bot MUST restrict `quarantine` to the service account.
11. The bot MUST record the Telegram user ID and the available identity snapshot.
12. The bot MUST record the recognition result and the moderation result or bypass state.
13. The bot MUST show only the current user's statistics to a non-admin user.
14. The bot MUST show the current user's hourly use.
15. The bot MUST return the catalogue `name` and `page_url` for a successful result.
16. The bot MUST show `ALOLA 1`, `@s1mb1o`, and `vino-svoe.ru` in the start message.
17. The bot MUST show a data notice before the first image request.
18. The bot MUST accept new Telegram updates while another photo is processed.
19. The bot MUST process accepted photos through one shared FIFO queue.
20. The queue MUST limit the number of concurrent workers.
21. The queue MUST reject new work when the configured capacity is full.
22. A queue-capacity rejection MUST NOT use the user rate limit.
23. The bot MUST restore queued and interrupted requests after a process restart.
24. The statistics response MUST show the current queue state.
25. A successful result MUST include a photo.
26. The result photo SHOULD use the official catalogue image.
27. The result photo MUST use the submitted accepted photo when the catalogue image is unavailable.
28. A successful result MUST show the wine color.
29. A successful result MUST show the sugar class.
30. A successful result MUST show the grape varieties.
31. The bot MUST show `нет данных` when a requested wine parameter is unavailable.
32. The bot MUST treat each photo in a Telegram album as a separate request.
33. The bot MUST add album photos to the queue in Telegram update order.
34. The bot MUST return one result for each album photo.
35. Each result MUST reply to its source photo.
36. Each album photo MUST use one request from the user rate limit.
37. The bot MUST ask the user to confirm an age of at least 18 years on `/start`.
38. The age confirmation MUST use `Мне есть 18 лет` and `Мне нет 18 лет` buttons.
39. The bot MUST store the age confirmation and its date in SQLite.
40. The bot MUST reject a photo before queueing when the user has not selected the adult confirmation.
41. A rejected photo MUST NOT use the user rate limit.
42. A rejected photo MUST NOT be downloaded or stored.
43. The bot MUST NOT require an identity document.
44. A successful result MUST contain the alcohol notice.
45. The age confirmation screen MUST contain the alcohol notice.
46. The bot MUST prepare an official catalogue image on a white 4:5 canvas.
47. The prepared image MUST have dimensions of 1024 by 1280 pixels.
48. The bot MUST detect the foreground from the alpha channel when transparency exists.
49. The bot MUST detect the foreground against white when transparency does not exist.
50. The prepared image MUST preserve the complete detected foreground.
51. The prepared image MUST keep 5% padding on its constrained canvas axis.
52. The bot MUST send only one queue receipt for one Telegram album.
53. The bot MUST continue to process each album photo as a separate request.
54. The bot MUST continue to return one result for each album photo.
55. The bot MUST identify the administrator by the configured Telegram user ID.
56. `BOT_ADMIN_USER_ID` MUST be explicit. The bot MUST NOT default to a real account.
57. The administrator `/stats` response MUST show aggregate statistics and personal hourly use.
58. The `/users` command MUST be available only to the administrator.
59. The `/users` command MUST show 20 users on one page.
60. The `/users` command MUST accept an optional positive page number.
61. A user entry MUST show the username, name, Telegram user ID, request count, hourly use, and last request time.
62. The `/reset_limit` command MUST be available only to the administrator.
63. `/reset_limit` without an argument MUST reset the administrator's current rate use.
64. `/reset_limit` MUST accept a Telegram user ID or a stored username.
65. A rate reset MUST preserve request history and statistics.
66. A rate reset MUST survive a process restart.
67. An administrator command MUST work only in the administrator's private chat.
68. A successful result for one non-album photo MUST show match feedback buttons.
69. The feedback buttons MUST use `✅ Совпало` and `❌ Не совпало` labels.
70. A result for a Telegram album photo MUST NOT show feedback buttons.
71. Only the user who sent the source photo MUST be able to submit its feedback.
72. The bot MUST accept only one feedback value for one request.
73. The bot MUST store the feedback value and submission time in SQLite.
74. Feedback MUST survive a process restart.
75. Feedback MUST remain linked to the recognition request.
76. The bot MUST remove the feedback buttons after a successful submission.
77. When moderation is enabled, the bot MUST use the `shieldgemma-2-4b-it` service.
78. When moderation is enabled, the bot MUST send the moderation image in a multipart
`image` field.
79. When moderation is enabled, the bot MUST read the moderation endpoint from
`endpoints.moderation` in `config.yaml`. The endpoint MUST use
`/upstream/shieldgemma-2-4b-it/classify` as the moderation path.
80. When moderation is enabled, the bot MUST use the service `flagged` list at threshold `0.5`.
81. An enabled moderation response MUST contain one score for each configured policy.
82. An enabled moderation response with an unknown or inconsistent policy MUST fail closed.
83. An enabled moderation transport or response error MUST stop storage and recognition.
84. A rejected image result MUST include the configured rejection illustration.
85. The rejection illustration MUST reply to the source photo.
86. The rejection caption MUST state that the content is inappropriate and was not sent to recognition.
87. The bot MUST remove the temporary processing status after it sends the rejection illustration.
88. A rejection illustration send failure MUST fall back to a text rejection status.
89. The bot MUST compute and store a perceptual hash after moderation or its configured bypass.
90. The bot MUST compute and store a difference hash after moderation or its configured bypass.
91. The bot MUST check blur after moderation or its configured bypass and before recognition.
92. The bot MUST check glare after moderation or its configured bypass and before recognition.
93. The bot MUST use SAM3 to check for a wine bottle before recognition.
94. The bot MUST use SAM3 to check for a usable label before recognition.
95. The SAM3 client MUST read its base URL from `endpoints.sam3` in `config.yaml`.
96. A quality service failure MUST NOT stop recognition.
97. A detected quality issue MUST NOT stop recognition.
98. The bot MUST store available quality results as advisory metadata.
99. The bot MUST read `endpoints.matcher` from `config.yaml` and request `k=4` ranked
candidates from its `/v1/match` path.
100. The bot MUST store every returned candidate rank, slug, score, and wine card.
101. The bot MUST use a configurable minimum Top-1 score.
102. The bot MUST use a configurable minimum Top-1 score margin.
103. The bot MUST answer `Не уверен` when either confidence condition fails.
104. A negative Top-1 feedback action MUST show the stored candidates at ranks 2 through 4.
When fewer candidates exist, the action shows the available candidates.
105. The alternative list MUST include `Ничего из этого`.
106. The bot MUST store the selected alternative rank and slug.
107. The bot MUST store an empty alternative selection.
108. A moderation rejection MUST show `Сообщить об ошибке фильтра`.
109. Only the source user MUST be able to submit a moderation filter error.
110. The bot MUST store no more than one moderation filter error per request.
111. A queue receipt MUST show the initial queue position.
112. A queue receipt MUST show an approximate wait.
113. The bot MUST edit the queue receipt when processing starts.
114. A successful result MUST show an `Открыть страницу вина` URL button.
115. The matcher response MUST contain at most four ranked candidates. An empty list MUST give
`Не уверен`.
116. A repeated negative feedback action MUST show the stored alternatives.
117. An alternative keyboard edit failure MUST send a new alternative message.
118. The bot MUST store the queue wait duration for each processing attempt.
119. The bot MUST store the duration of each main processing step.
120. A step timing MUST contain the step start time in Unix milliseconds.
121. A step timing MUST contain an `ok`, `failed`, or `cancelled` outcome.
122. Step timing rows MUST be append-only.
123. The bot MUST write each stored step timing to the service journal.
124. The measured steps MUST include Telegram download, image preparation, moderation,
fingerprint calculation, image storage, quality inspection, recognition, candidate storage,
and result delivery when the step applies.
125. The system MUST provide a separate administration web service.
126. The administration web service MUST use the existing SQLite database.
127. The administration web service MUST require password authentication.
128. The administration web service MUST restrict access to configured CIDR networks.
129. The default allowed networks MUST include only localhost.
130. The administration web service MUST show aggregate statistics.
131. The administration web service MUST show a paginated user list.
132. The administration web service MUST show a paginated recent request list.
133. A request detail page MUST show status, timings, moderation metadata, quality metadata,
recognition metadata, feedback, and candidates.
134. The administration web service MUST show moderation filter error reports.
135. The administration web service MUST reset one user's current rate-limit window.
136. A rate-limit reset from the administration web service MUST preserve request history.
137. The administration web service MUST let the administrator request a safe retry.
138. A retry action MUST require a prior safe moderation result or explicit non-production
moderation bypass.
139. A retry action MUST NOT accept an unsafe request or a request with an incomplete
moderation step.
140. The bot MUST send an administration retry through the existing work queue.
141. The bot MUST run moderation again during an administration retry when moderation is enabled.
142. A retry request MUST survive a restart of the web service or bot service.
143. The administration web service MUST NOT serve accepted source files directly.
144. The administration web service MUST NOT serve quarantine images.
145. Every state-changing web form MUST include CSRF protection.
146. The production administration service MUST use TCP port `28003` on gx10.
147. The bot MUST request SAM3 masks during quality inspection.
148. The bot MUST validate a SAM3 mask against the moderation image dimensions.
149. The bot MUST persist full-fidelity visual pipeline artifacts only after safe moderation
or an explicit non-production moderation bypass.
150. The bot MAY create only a server-side censored preview from an unsafe image.
151. The pipeline artifacts MUST include the exact matcher input.
152. The pipeline artifacts MUST include the normalized moderation image.
153. The pipeline artifacts MUST include each accepted SAM3 mask.
154. The pipeline artifacts MUST include a combined SAM3 overlay.
155. The combined overlay MUST show masks, boxes, prompt labels, and scores.
156. The pipeline artifacts MUST include the selected bottle box crop and masked cutout.
157. The pipeline artifacts MUST include the selected label box crop and masked cutout.
158. The pipeline artifacts SHOULD include the final Telegram result image.
159. An artifact generation failure MUST NOT stop recognition.
160. A request detail page MUST show the ordered pipeline artifacts.
161. The administration web service MUST serve an artifact only when the current request
has a safe moderation result or explicit non-production moderation bypass.
162. An artifact route MUST use the existing authentication and network restrictions.
163. An artifact route MUST NOT resolve a file outside `BOT_DATA_ROOT/artifacts`.
164. A request retry MUST replace the artifact index for the request.
165. The system MUST provide a command that reconstructs artifacts for a previously accepted
request without sending a Telegram message.
166. A censored preview MUST use an irreversible server-side transformation.
167. A censored preview MUST reduce the longest side to 24 pixels before enlargement.
168. A censored preview MUST have a maximum longest side of 768 pixels.
169. A censored preview MUST apply a Gaussian blur with a radius of 18 pixels after enlargement.
170. A censored preview MUST use JPEG encoding.
171. A censored preview artifact MUST use the `censored` exposure class.
172. A full-fidelity artifact MUST use the `safe` exposure class.
173. The administration service MUST serve a `censored` artifact only when the current request has an unsafe moderation result.
174. The administration service MUST NOT use CSS blur as the only censorship control.
175. The reconstruction command MUST create only a censored preview for a previously quarantined request.
176. The bot MUST NOT select a matcher pipeline. The matcher configuration selects it.
177. The bot MUST store the pipeline name of each matcher answer.
178. The bot process MUST provide `POST /api/v1/recognize` for internal tests.
179. The endpoint MUST accept one multipart `image` field.
180. The endpoint MUST use the same FIFO queue as Telegram requests.
181. The endpoint MUST use the same configured moderation or non-production bypass, quality, recognition,
storage, artifact, and timing steps.
182. The endpoint MUST wait for processing to reach a terminal status.
183. The endpoint MUST return a JSON response.
184. The JSON response MUST contain the request ID, status, matcher pipeline, moderation metadata,
quality metadata, recognition metadata, candidates, wine parameters, and step timings. The
moderation metadata MUST contain `performed`, `bypassed`, and nullable `safe` fields.
185. The endpoint MUST enforce `BOT_MAX_IMAGE_BYTES`.
186. The endpoint MUST keep the unmoderated image in memory.
187. The endpoint MUST NOT write an unmoderated image to a temporary upload file.
188. The endpoint MUST require a bearer token from `BOT_HTTP_API_TOKEN`.
189. The endpoint MUST restrict access to `BOT_HTTP_API_ALLOWED_NETWORKS`.
190. The default API networks MUST include only localhost and `192.168.86.0/24`.
191. The production HTTP recognition API MUST use TCP port `28002` on gx10.
192. The HTTP recognition API MUST publish OpenAPI and Swagger UI.
193. An API request MUST be exempt from the Telegram per-user rate limit.
194. The configured queue capacity MUST apply to an API request.
195. The API MUST return HTTP 503 when the shared queue is full or unavailable.
196. An API response MUST NOT contain a quarantine file or storage path.
197. The service MUST NOT restore an interrupted API request as a Telegram request.
198. The administration interface MUST show an API request and its source.
199. The administration interface MUST NOT offer Telegram retry for an API request.
200. The HTTP API MUST add `qr_urls` to a matched wine when its matcher wine card contains a QR URL.
201. The HTTP API MUST add `qr_urls` to a candidate wine when its matcher wine card contains a QR URL.
202. The HTTP API MUST omit `qr_urls` when a wine has no valid QR URL.
203. The service MUST accept only `http` and `https` QR URLs.
204. The service MUST read QR URLs from the matcher wine card.
205. The bot MUST read the wine card of each candidate from the matcher answer.
206. The bot MUST NOT read a local catalogue file or a local wine code map.
207. A stored candidate without a wine card MUST use its slug as the wine name.
208. A successful result MUST show the wine producer.
209. The exact matcher input artifact MUST keep its JPEG, PNG, or WebP media type.
210. The service MUST accept result pages only from `vino-svoe.ru` and `www.vino-svoe.ru`.
     A result page MUST use HTTPS on the standard HTTPS port.
211. The API MUST apply its client rate limit before it reads an upload body.
212. The API MUST apply its in-flight request limit before it reads an upload body.
213. The administration listener MUST use loopback unless a TLS proxy is its only published route.
214. Production MUST delete terminal request data after 30 days.
215. Retention MUST delete source files, artifacts, request rows, and inactive user profiles.
216. Retention MUST NOT delete an active request.
217. The system MUST provide a command for an early user-requested deletion.
218. The deletion command MUST delete source files, artifacts, request rows, and the user profile.
219. The HTTP service MUST provide separate liveness and readiness routes.
220. Readiness MUST check the database, queue, and configured upstream TCP endpoints.
221. Source storage and matcher requests MUST preserve JPEG, PNG, and WebP media types.
222. The project MUST provide a deterministic host demo that needs no private service.
223. `BOT_HTTP_API_TOKEN` MUST contain at least 32 characters.
224. Retention MUST delete the complete artifact directory of each expired request.

## Non-functional requirements

1. Logs MUST NOT contain secrets or image bytes.
2. Logs MUST NOT contain a username or a personal name.
3. One failed request MUST NOT stop long polling.
4. SQLite MUST use WAL mode.
5. An image write MUST use an atomic rename.
6. All upstream calls MUST have timeouts.
7. The bot MUST stop cleanly on `SIGTERM`.
8. One queue job failure MUST NOT stop a queue worker.
9. A Telegram queue job MUST NOT keep image bytes in memory while it waits.
10. An API queue job MAY keep one bounded image in memory while it waits.
11. A catalogue image failure MUST NOT change a successful recognition status.
12. The bot MUST validate and normalize a catalogue image before it sends the image to Telegram.
13. The result image preparation MUST NOT call another model or service.
14. The album receipt tracker MUST expire old media group identifiers.
15. The album receipt tracker MUST have a fixed capacity.
16. The administration web interface MUST support the browser system dark theme.
17. The administration web service MUST add restrictive browser security headers.

## Out of scope

1. The first release does not accept image documents.
2. The administration UI is not public.
