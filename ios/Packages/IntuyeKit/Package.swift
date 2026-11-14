// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "IntuyeKit",
    platforms: [.iOS("26.0"), .macOS("26.0")],
    products: [.library(name: "IntuyeKit", targets: ["IntuyeKit"])],
    targets: [
        .target(name: "IntuyeKit"),
        .testTarget(name: "IntuyeKitTests", dependencies: ["IntuyeKit"]),
    ]
)
