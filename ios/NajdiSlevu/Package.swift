// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "NajdiSlevu",
    products: [
        .library(name: "NajdiSlevu", targets: ["NajdiSlevu"]),
    ],
    dependencies: [
        .package(
            url: "https://github.com/apple/swift-openapi-generator",
            from: "1.0.0"
        ),
        .package(
            url: "https://github.com/apple/swift-openapi-runtime",
            from: "1.0.0"
        ),
        .package(
            url: "https://github.com/apple/swift-openapi-urlsession",
            from: "1.0.0"
        ),
    ],
    targets: [
        .target(
            name: "NajdiSlevu",
            dependencies: [
                .product(name: "OpenAPIRuntime", package: "swift-openapi-runtime"),
                .product(name: "OpenAPIURLSession", package: "swift-openapi-urlsession"),
            ],
            plugins: [
                .plugin(name: "OpenAPIGenerator", package: "swift-openapi-generator"),
            ]
        ),
    ]
)
