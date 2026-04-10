// Generated from api/openapi.yaml
// Regenerate: swift package plugin generate-code-from-openapi --target NajdiSlevu
// (requires swift-openapi-generator build plugin — see Package.swift)
//
// NOTE: Codable / Sendable are part of the Swift standard library and
//       do not require Foundation.  Date fields are modelled as String
//       (ISO 8601) so no DateFormatter dependency is introduced here.

// MARK: - Supermarket

public struct Supermarket: Codable, Sendable, Identifiable {
    public let id: Int
    public let name: String
}

// MARK: - Discount

public struct Discount: Codable, Sendable, Identifiable {
    public let id: Int
    public let supermarket: Supermarket?
    public let name: String
    public let originalPrice: Double?
    public let discountedPrice: Double
    public let discountPct: Double?
    /// ISO 8601 date string, e.g. "2026-04-07"
    public let validFrom: String?
    /// ISO 8601 date string, e.g. "2026-04-13"
    public let validTo: String?
    public let canonicalKey: String?
    public let canonicalBrand: String?
    public let canonicalProductType: String?
    public let canonicalQuantityValue: Double?
    public let canonicalQuantityUnit: String?

    private enum CodingKeys: String, CodingKey {
        case id
        case supermarket
        case name
        case originalPrice         = "original_price"
        case discountedPrice       = "discounted_price"
        case discountPct           = "discount_pct"
        case validFrom             = "valid_from"
        case validTo               = "valid_to"
        case canonicalKey          = "canonical_key"
        case canonicalBrand        = "canonical_brand"
        case canonicalProductType  = "canonical_product_type"
        case canonicalQuantityValue = "canonical_quantity_value"
        case canonicalQuantityUnit  = "canonical_quantity_unit"
    }
}

// MARK: - DiscountPage

public struct DiscountPage: Codable, Sendable {
    public let items: [Discount]
    public let total: Int
    public let page: Int
    public let pageSize: Int

    private enum CodingKeys: String, CodingKey {
        case items
        case total
        case page
        case pageSize = "page_size"
    }
}

// MARK: - PricePoint

public struct PricePoint: Codable, Sendable {
    /// ISO 8601 date-time string, e.g. "2026-03-15T10:30:00Z"
    public let scrapedAt: String
    public let supermarket: String?
    public let discountedPrice: Double
    public let originalPrice: Double?
    public let canonicalKey: String?

    private enum CodingKeys: String, CodingKey {
        case scrapedAt       = "scraped_at"
        case supermarket
        case discountedPrice = "discounted_price"
        case originalPrice   = "original_price"
        case canonicalKey    = "canonical_key"
    }
}

// MARK: - PriceHistory

public struct PriceHistory: Codable, Sendable {
    public let canonicalKey: String
    public let history: [PricePoint]

    private enum CodingKeys: String, CodingKey {
        case canonicalKey = "canonical_key"
        case history
    }
}

// MARK: - Auth

public struct UserCredentials: Codable, Sendable {
    public let email: String
    public let password: String
}

public struct User: Codable, Sendable, Identifiable {
    public let id: Int
    public let email: String
    /// ISO 8601 date-time string
    public let createdAt: String?

    private enum CodingKeys: String, CodingKey {
        case id
        case email
        case createdAt = "created_at"
    }
}

public struct AuthToken: Codable, Sendable {
    public let accessToken: String
    public let tokenType: String
    public let expiresIn: Int?
    public let user: User

    private enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType   = "token_type"
        case expiresIn   = "expires_in"
        case user
    }
}

// MARK: - Watchlist

public struct WatchlistItem: Codable, Sendable, Identifiable {
    public let id: Int
    public let keyword: String
}

// MARK: - Device

public enum DevicePlatform: String, Codable, Sendable {
    case ios
    case android
}

public struct Device: Codable, Sendable, Identifiable {
    public let id: Int
    public let token: String
    public let platform: DevicePlatform
    /// ISO 8601 date-time string
    public let registeredAt: String?

    private enum CodingKeys: String, CodingKey {
        case id
        case token
        case platform
        case registeredAt = "registered_at"
    }
}

public struct DeviceRegistration: Codable, Sendable {
    public let token: String
    public let platform: DevicePlatform
}

// MARK: - Error

public struct APIError: Codable, Sendable, Error {
    public let detail: String
    public let code: String?
}
