import Foundation

@MainActor
final class AppPreferences: ObservableObject {
    private enum Key {
        static let ageAccepted = "age_accepted"
        static let encoder = "encoder"
        static let segmenter = "segmenter"
        static let disCompute = "dis_compute"
        static let encoderCompute = "encoder_compute"
        static let debugServer = "debug_server"
        static let acceleratorProbeStatus = "accelerator_probe_status"
    }

    private let defaults: UserDefaults

    @Published var ageAccepted: Bool { didSet { defaults.set(ageAccepted, forKey: Key.ageAccepted) } }
    @Published var encoder: ImageEncoderID { didSet { defaults.set(encoder.rawValue, forKey: Key.encoder) } }
    @Published var segmenter: SegmenterID { didSet { defaults.set(segmenter.rawValue, forKey: Key.segmenter) } }
    @Published var disComputeMode: ComputeMode { didSet { defaults.set(disComputeMode.rawValue, forKey: Key.disCompute) } }
    @Published var encoderComputeMode: ComputeMode { didSet { defaults.set(encoderComputeMode.rawValue, forKey: Key.encoderCompute) } }
    @Published var debugServerEnabled: Bool { didSet { defaults.set(debugServerEnabled, forKey: Key.debugServer) } }
    @Published var acceleratorProbeStatus: String {
        didSet { defaults.set(acceleratorProbeStatus, forKey: Key.acceleratorProbeStatus) }
    }

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        ageAccepted = defaults.bool(forKey: Key.ageAccepted)
        encoder = ImageEncoderID(rawValue: defaults.string(forKey: Key.encoder) ?? "") ?? .siglip2BaseNaFlexP512
        segmenter = SegmenterID(rawValue: defaults.string(forKey: Key.segmenter) ?? "") ?? .dis
        disComputeMode = ComputeMode(rawValue: defaults.string(forKey: Key.disCompute) ?? "") ?? .automatic
        encoderComputeMode = ComputeMode(rawValue: defaults.string(forKey: Key.encoderCompute) ?? "") ?? .automatic
        debugServerEnabled = defaults.bool(forKey: Key.debugServer)
        acceleratorProbeStatus = defaults.string(forKey: Key.acceleratorProbeStatus) ?? ""
    }
}
