// Generated from api/openapi.yaml
// Regenerate: swift package plugin generate-code-from-openapi --target NajdiSlevu

// MARK: - Supporting types

public struct HealthResponse: Codable, Sendable {
    public let status: String
}

public struct DiscountListParams: Sendable {
    public var supermarket: String?
    public var minDiscountPct: Double?
    /// ISO 8601 date, e.g. "2026-04-10"
    public var validOn: String?
    public var q: String?
    public var page: Int
    public var pageSize: Int

    public init(
        supermarket: String? = nil,
        minDiscountPct: Double? = nil,
        validOn: String? = nil,
        q: String? = nil,
        page: Int = 1,
        pageSize: Int = 50
    ) {
        self.supermarket = supermarket
        self.minDiscountPct = minDiscountPct
        self.validOn = validOn
        self.q = q
        self.page = page
        self.pageSize = pageSize
    }
}

// MARK: - APIClient protocol

/// Typed API client generated from the Najdi Slevu OpenAPI spec.
/// Swap `MockAPIClient` for `LiveAPIClient` once the real backend is running.
public protocol APIClientProtocol: Sendable {
    func getHealth() async throws -> HealthResponse
    func listSupermarkets() async throws -> [Supermarket]
    func listDiscounts(params: DiscountListParams) async throws -> DiscountPage
    func getDiscount(id: Int) async throws -> Discount
    func getDiscountHistory(id: Int) async throws -> PriceHistory
    func register(credentials: UserCredentials) async throws -> AuthToken
    func login(credentials: UserCredentials) async throws -> AuthToken
    func listWatchlist() async throws -> [WatchlistItem]
    func addWatchlistItem(keyword: String) async throws -> WatchlistItem
    func removeWatchlistItem(keyword: String) async throws
    func registerDevice(registration: DeviceRegistration) async throws -> Device
}
