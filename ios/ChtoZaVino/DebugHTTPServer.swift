#if DEBUG
import Foundation
import Network

final class DebugHTTPServer: @unchecked Sendable {
    typealias Recognition = @Sendable (Data, Int) async throws -> RecognitionOutput
    typealias Configuration = @Sendable () async -> (SegmenterID, ImageEncoderID)

    static let port: UInt16 = 18088
    static let maximumImageBytes = 20 * 1024 * 1024

    private let listener: NWListener
    private let queue = DispatchQueue(label: "chtozavino.debug-http")
    private let inferenceGate = InferenceGate()
    private let packVersion: String
    private let wineCount: Int
    private let recognition: Recognition
    private let configuration: Configuration

    init(
        packVersion: String,
        wineCount: Int,
        configuration: @escaping Configuration,
        recognition: @escaping Recognition
    ) throws {
        guard let port = NWEndpoint.Port(rawValue: Self.port) else {
            throw AppError.message("Некорректный порт HTTP-сервера.")
        }
        listener = try NWListener(using: .tcp, on: port)
        self.packVersion = packVersion
        self.wineCount = wineCount
        self.configuration = configuration
        self.recognition = recognition
    }

    func start() {
        listener.newConnectionHandler = { [weak self] connection in self?.accept(connection) }
        listener.start(queue: queue)
    }

    func stop() { listener.cancel() }

    static func matchLimit(_ raw: String?) throws -> Int {
        guard let raw, !raw.isEmpty else { return 20 }
        guard let value = Int(raw) else { throw AppError.message("k must be an integer") }
        guard (1...20).contains(value) else { throw AppError.message("k must be from 1 through 20") }
        return value
    }

    private func accept(_ connection: NWConnection) {
        connection.start(queue: queue)
        receive(connection, buffer: Data())
    }

    private func receive(_ connection: NWConnection, buffer: Data) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: Self.maximumImageBytes + 131_072) {
            [weak self] data, _, complete, error in
            guard let self else { return }
            if error != nil { connection.cancel(); return }
            var next = buffer
            if let data { next.append(data) }
            if next.count > Self.maximumImageBytes + 131_072 {
                self.send(connection, status: 413, json: ["detail": "image exceeds 20 MiB"])
                return
            }
            if let request = HTTPRequest.parse(next) {
                self.handle(request, connection: connection)
            } else if complete {
                self.send(connection, status: 400, json: ["detail": "invalid request"])
            } else {
                self.receive(connection, buffer: next)
            }
        }
    }

    private func handle(_ request: HTTPRequest, connection: NWConnection) {
        if request.method == "GET", request.path == "/healthz" {
            Task {
                let (segmenter, encoder) = await configuration()
                send(connection, status: 200, json: [
                    "status": "ok",
                    "port": Int(Self.port),
                    "pack_version": packVersion,
                    "wine_count": wineCount,
                    "segmenter": segmenter.technicalTitle,
                    "encoder": encoder.rawValue,
                ])
            }
            return
        }
        let isPredict = request.path == "/v1/eval/predict"
        let isMatch = request.path == "/v1/match"
        guard isPredict || isMatch else {
            send(connection, status: 404, json: ["detail": "not found"])
            return
        }
        guard request.method == "POST" else {
            send(connection, status: 405, json: ["detail": "method not allowed"])
            return
        }
        do {
            let limit = try isMatch ? Self.matchLimit(request.query["k"]) : 1
            let image = try request.multipartImage()
            guard !image.isEmpty else { throw HTTPFailure(status: 400, detail: "image is empty") }
            guard image.count <= Self.maximumImageBytes else {
                throw HTTPFailure(status: 413, detail: "image exceeds 20 MiB")
            }
            Task {
                let start = ContinuousClock().now
                do {
                    let output = try await inferenceGate.run {
                        try await recognition(image, limit)
                    }
                    let latency = Self.milliseconds(start.duration(to: ContinuousClock().now))
                    if isPredict {
                        send(connection, status: 200, json: ["slug": output.matches.first?.wine.wineSlug ?? ""])
                    } else {
                        send(connection, status: 200, json: [
                            "pipeline": "ios-\(output.segmenter.rawValue)-\(output.encoder.rawValue)",
                            "latency_ms": latency,
                            "timings_ms": [
                                "segmentation": output.segmentationMilliseconds,
                                "embedding": output.embeddingMilliseconds,
                                "search": output.searchMilliseconds,
                            ],
                            "candidates": output.matches.enumerated().map { offset, match in
                                [
                                    "rank": offset + 1,
                                    "slug": match.wine.wineSlug,
                                    "score": match.score,
                                    "wine": Self.wineJSON(match.wine),
                                ] as [String: Any]
                            },
                        ])
                    }
                } catch {
                    send(connection, status: 502, json: ["detail": error.localizedDescription])
                }
            }
        } catch let failure as HTTPFailure {
            send(connection, status: failure.status, json: ["detail": failure.detail])
        } catch {
            send(connection, status: 400, json: ["detail": error.localizedDescription])
        }
    }

    private func send(_ connection: NWConnection, status: Int, json object: [String: Any]) {
        let body = (try? JSONSerialization.data(withJSONObject: object)) ?? Data("{}".utf8)
        let reason: String = switch status {
        case 200: "OK"
        case 400: "Bad Request"
        case 404: "Not Found"
        case 405: "Method Not Allowed"
        case 413: "Payload Too Large"
        case 415: "Unsupported Media Type"
        case 422: "Unprocessable Entity"
        default: "Bad Gateway"
        }
        var response = Data("HTTP/1.1 \(status) \(reason)\r\n".utf8)
        response.append(Data("Content-Type: application/json; charset=utf-8\r\n".utf8))
        response.append(Data("Content-Length: \(body.count)\r\n".utf8))
        response.append(Data("Cache-Control: no-store\r\nConnection: close\r\n\r\n".utf8))
        response.append(body)
        connection.send(content: response, completion: .contentProcessed { _ in connection.cancel() })
    }

    private static func wineJSON(_ wine: WineCard) -> [String: Any] {
        [
            "name": wine.name,
            "page_url": wine.pageURL,
            "producer": wine.producer ?? NSNull(),
            "category": wine.category ?? NSNull(),
            "region": wine.region ?? NSNull(),
            "color": wine.color ?? NSNull(),
            "grapes": wine.grapes ?? NSNull(),
            "sugar": NSNull(),
            "image_url": NSNull(),
            "qr_urls": [],
        ]
    }

    private static func milliseconds(_ duration: Duration) -> Double {
        let value = duration.components
        return Double(value.seconds) * 1_000 + Double(value.attoseconds) / 1_000_000_000_000_000
    }
}

private actor InferenceGate {
    func run<T: Sendable>(_ operation: @Sendable () async throws -> T) async rethrows -> T {
        try await operation()
    }
}

private struct HTTPFailure: Error {
    let status: Int
    let detail: String
}

private struct HTTPRequest {
    let method: String
    let path: String
    let query: [String: String]
    let headers: [String: String]
    let body: Data

    static func parse(_ data: Data) -> HTTPRequest? {
        let marker = Data("\r\n\r\n".utf8)
        guard let range = data.range(of: marker),
              let head = String(data: data[..<range.lowerBound], encoding: .utf8) else { return nil }
        let lines = head.components(separatedBy: "\r\n")
        guard let requestLine = lines.first else { return nil }
        let parts = requestLine.split(separator: " ")
        guard parts.count >= 2 else { return nil }
        var headers: [String: String] = [:]
        for line in lines.dropFirst() {
            let pair = line.split(separator: ":", maxSplits: 1).map(String.init)
            if pair.count == 2 { headers[pair[0].lowercased()] = pair[1].trimmingCharacters(in: .whitespaces) }
        }
        let contentLength = Int(headers["content-length"] ?? "0") ?? 0
        let bodyStart = range.upperBound
        guard data.count >= bodyStart + contentLength else { return nil }
        let target = String(parts[1])
        let components = URLComponents(string: target)
        return HTTPRequest(
            method: String(parts[0]),
            path: components?.path ?? target,
            query: Dictionary(uniqueKeysWithValues: (components?.queryItems ?? []).compactMap {
                item in item.value.map { (item.name, $0) }
            }),
            headers: headers,
            body: data.subdata(in: bodyStart..<(bodyStart + contentLength))
        )
    }

    func multipartImage() throws -> Data {
        guard let contentType = headers["content-type"], contentType.hasPrefix("multipart/form-data"),
              let boundaryPart = contentType.components(separatedBy: ";").first(where: {
                  $0.trimmingCharacters(in: .whitespaces).hasPrefix("boundary=")
              }) else {
            throw HTTPFailure(status: 415, detail: "multipart/form-data is required")
        }
        let boundary = boundaryPart.trimmingCharacters(in: .whitespaces)
            .replacingOccurrences(of: "boundary=", with: "")
            .trimmingCharacters(in: CharacterSet(charactersIn: "\""))
        let separator = Data(("--" + boundary).utf8)
        let headerMarker = Data("\r\n\r\n".utf8)
        let endMarker = Data(("\r\n--" + boundary).utf8)
        var searchStart = body.startIndex
        while let boundaryRange = body.range(of: separator, in: searchStart..<body.endIndex) {
            let partStart = boundaryRange.upperBound
            guard let headerRange = body.range(of: headerMarker, in: partStart..<body.endIndex) else { break }
            let headerData = body[partStart..<headerRange.lowerBound]
            let headerText = String(data: headerData, encoding: .utf8) ?? ""
            if headerText.contains("name=\"image\"") {
                let valueStart = headerRange.upperBound
                guard let end = body.range(of: endMarker, in: valueStart..<body.endIndex) else {
                    throw HTTPFailure(status: 400, detail: "invalid multipart body")
                }
                return body.subdata(in: valueStart..<end.lowerBound)
            }
            searchStart = partStart
        }
        throw HTTPFailure(status: 422, detail: "image is required")
    }
}
#else
import Foundation

final class DebugHTTPServer {
    typealias Recognition = @Sendable (Data, Int) async throws -> RecognitionOutput
    typealias Configuration = @Sendable () async -> (SegmenterID, ImageEncoderID)
    init(
        packVersion: String,
        wineCount: Int,
        configuration: @escaping Configuration,
        recognition: @escaping Recognition
    ) throws {
        throw AppError.message("HTTP-сервер доступен только в debug build.")
    }
    func start() {}
    func stop() {}
}
#endif
