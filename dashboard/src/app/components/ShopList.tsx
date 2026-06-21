import React from 'react';

type Shop = {
  id: string;
  name: string;
  address: string;
  detailed_address?: string;
  building_name?: string;
  floor?: string;
  room_number?: string;
  raw_rating: number;
  review_count: number;
  has_review_event: boolean;
  is_shop_in_shop: boolean;
  is_suspicious: boolean;
  sis_sibling_names?: string;
};

interface Props {
  shops: Shop[];
}

const ShopList: React.FC<Props> = ({ shops }) => {
  // Determine credibility score and state based on review event and SIS status
  const getCredibility = (shop: Shop) => {
    if (shop.is_shop_in_shop) {
      return { score: 35, level: '낮음', className: 'low', color: 'var(--color-sis)' };
    }
    if (shop.is_suspicious) {
      return { score: 50, level: '주의', className: 'medium', color: '#f39c12' };
    }
    if (shop.has_review_event) {
      return { score: 70, level: '보통', className: 'medium', color: 'var(--color-rating)' };
    }
    return { score: 100, level: '높음', className: 'high', color: 'var(--color-clean)' };
  };

  return (
    <div>
      {shops.length === 0 ? (
        <div className="glass-panel empty-state fade-in-up">
          <div className="empty-icon">🔍</div>
          <p>조건에 부합하는 맛집이 없습니다.</p>
          <p style={{ fontSize: '0.8rem', marginTop: '4px', opacity: 0.7 }}>필터 또는 검색어를 조정해 보세요.</p>
        </div>
      ) : (
        <div className="shops-grid">
          {shops.map((shop) => {
            const credibility = getCredibility(shop);
            const cardModifier = shop.is_shop_in_shop 
              ? 'is-sis' 
              : shop.is_suspicious
                ? 'is-suspicious'
                : shop.has_review_event 
                  ? 'is-event' 
                  : 'is-clean';

            // Construct granular address string
            const fullDetail = [
              shop.detailed_address, // Lot number
              shop.building_name,
              shop.floor,
              shop.room_number
            ].filter(Boolean).join(' ');

            return (
              <div 
                key={shop.id} 
                className={`shop-card ${cardModifier} fade-in-up`}
              >
                <div>
                  <div className="shop-category">
                    {shop.is_shop_in_shop ? '위장 의심' : shop.is_suspicious ? '밀집 의심' : '요기요 등록점'}
                  </div>

                  <div className="shop-info-top">
                    <h3 className="shop-name">{shop.name}</h3>
                    <div className="shop-rating-box">
                      <span className="rating-value">
                        ⭐ {shop.raw_rating.toFixed(1)}
                      </span>
                      <span className="review-count">
                        {shop.review_count} reviews
                      </span>
                    </div>
                  </div>

                  <p className="shop-address">
                    <span className="base-addr">{shop.address}</span>
                    <span className="detail-addr" style={{ marginLeft: '6px', opacity: 0.8 }}>
                      {fullDetail}
                    </span>
                  </p>

                  <div className="badge-row">
                    {shop.is_shop_in_shop && (
                      <span className="tag-badge sis">
                        🚨 위장 가맹점(SIS)
                      </span>
                    )}
                    {shop.is_suspicious && (
                      <span className="tag-badge suspicious" style={{ backgroundColor: '#f39c12', color: 'white' }}>
                        ⚠️ 의심 매장 (밀집)
                      </span>
                    )}
                    {shop.has_review_event && (
                      <span className="tag-badge event">
                        🎈 리뷰 이벤트
                      </span>
                    )}
                    {!shop.is_shop_in_shop && !shop.is_suspicious && !shop.has_review_event && (
                      <span className="tag-badge clean">
                        ✅ 클린 안심 매장
                      </span>
                    )}
                  </div>
                </div>

                <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {/* Rating Credibility Gauge Meter */}
                  <div className="credibility-section">
                    <div className="credibility-label">
                      <span>평점 신뢰성</span>
                      <span className={`credibility-value ${credibility.className}`}>
                        {credibility.level} ({credibility.score}%)
                      </span>
                    </div>
                    <div className="gauge-track">
                      <div 
                        className="gauge-fill" 
                        style={{ 
                          width: `${credibility.score}%`, 
                          backgroundColor: credibility.color 
                        }}
                      ></div>
                    </div>
                  </div>

                  {/* Sibling Brands list (Only for Shop in Shops) */}
                  {shop.is_shop_in_shop && shop.sis_sibling_names && (
                    <div className="sis-relation-box">
                      <div className="sis-relation-title">동일 사업장 타 입점 브랜드</div>
                      <div className="sis-siblings-list">
                        {shop.sis_sibling_names.split(',').map((name, idx) => (
                          <span key={idx} className="sis-sibling-tag" title={name.trim()}>
                            🍕 {name.trim()}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ShopList;
