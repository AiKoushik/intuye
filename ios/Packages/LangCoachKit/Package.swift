// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "LangCoachKit",
    platforms: [.iOS("26.0"), .macOS("26.0")],
    products: [.library(name: "LangCoachKit", targets: ["LangCoachKit"])],
    targets: [
        .target(name: "LangCoachKit"),
        .testTarget(name: "LangCoachKitTests", dependencies: ["LangCoachKit"]),
    ]
)
