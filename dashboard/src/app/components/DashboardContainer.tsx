"use client";
import React, { useEffect, useState, useMemo, useRef } from 'react';
import dynamic from 'next/dynamic';
import ShopList from './ShopList';
import Levenshtein from 'fast-levenshtein';

// Pure dynamic import without persistent rendering hacks
const Map = dynamic(() => import('./Map'), {
  ssr: false,
  loading: () => (
    <div className="map-container-wrapper" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--color-card)', height: '650px', borderRadius: '20px' }}>
      <div className="spinner"></div>
    </div>
  )
});

export type Shop = {
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
  sis_sibling_names?: string;
  latitude: number;
  longitude: number;
  is_suspicious?: boolean;
  company_name?: string;
  risk_score?: number;
  is_ghost_kitchen?: boolean;
};

const DashboardContainer: React.FC = () => {
  const [shops, setShops] = useState<Shop[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [viewMode, setViewMode] = useState<'list' | 'map'>('list');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [excludeShopInShop, setExcludeShopInShop] = useState<boolean>(false);
  const [excludeReviewEvent, setExcludeReviewEvent] = useState<boolean>(false);

  // 시군구 관련 상태 추가
  const [sigungus, setSigungus] = useState<string[]>([]);
  const [sigunguLoading, setSigunguLoading] = useState<boolean>(true);
  const [selectedSigungu, setSelectedSigungu] = useState<string>('');
  const [sigunguSearch, setSigunguSearch] = useState<string>('');
  const [showDropdown, setShowDropdown] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  const dropdownRef = useRef<HTMLDivElement>(null);

  // 클릭 외부 감지 (자동완성 창 닫기)
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // 1. 처음 마운트 시 시군구 데이터만 가져옴
  useEffect(() => {
    const fetchSigungus = async () => {
      try {
        setSigunguLoading(true);
        const response = await fetch('/api/sigungu');
        const data = await response.json();
        if (data && Array.isArray(data.sigungus)) {
          setSigungus(data.sigungus);
          setLastUpdated(data.lastUpdated || '');
        } else if (Array.isArray(data)) {
          setSigungus(data);
        }
      } catch (err) {
        console.error('시군구 목록을 불러오는 중 오류 발생:', err);
      } finally {
        setSigunguLoading(false);
      }
    };
    fetchSigungus();
  }, []);

  // 2. 시군구가 선택되었을 때만 해당하는 상점 데이터를 가져옴
  useEffect(() => {
    if (!selectedSigungu) {
      setShops([]);
      return;
    }

    const fetchShops = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`/api/shops?sigungu=${encodeURIComponent(selectedSigungu)}`);
        const data: Shop[] = await response.json();

        const processedData = data.map(shop => {
          const shopName = shop.name || "";
          const companyName = shop.company_name || "";

          let score = 0;

          if (shopName && companyName) {
            const distance = Levenshtein.get(shopName, companyName);
            const maxLen = Math.max(shopName.length, companyName.length);
            const differenceRatio = maxLen > 0 ? distance / maxLen : 0;
            score += Math.min(Math.round(differenceRatio * 50), 50);
          }

          const riskKeywords = ['푸드', '딜리버리', '키친', '컴퍼니', ' F&B', '앤비'];
          const hasRiskKeyword = riskKeywords.some(keyword => companyName.toLowerCase().includes(keyword));
          if (hasRiskKeyword) {
            score += 50;
          }

          const finalRiskScore = Math.min(score, 100);

          return {
            ...shop,
            risk_score: finalRiskScore,
            is_ghost_kitchen: finalRiskScore >= 70
          };
        });

        setShops(processedData);
      } catch (err) {
        setError('데이터를 불러오는 중 문제가 발생했습니다.');
      } finally {
        setLoading(false);
      }
    };
    fetchShops();
  }, [selectedSigungu]);

  // 입력된 텍스트 기준 시군구 목록 필터링
  const filteredSigungus = useMemo(() => {
    if (!sigunguSearch.trim()) {
      return sigungus;
    }
    const query = sigunguSearch.toLowerCase();
    return sigungus.filter(s => s.toLowerCase().includes(query));
  }, [sigungus, sigunguSearch]);

  const filteredShops = useMemo(() => {
    let result = [...shops];
    if (excludeShopInShop) result = result.filter(shop => !shop.is_shop_in_shop);
    if (excludeReviewEvent) result = result.filter(shop => !shop.has_review_event);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(shop => shop.name.toLowerCase().includes(q) || shop.address.toLowerCase().includes(q));
    }
    result.sort((a, b) => b.raw_rating - a.raw_rating);
    return result;
  }, [shops, excludeShopInShop, excludeReviewEvent, searchQuery]);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header className="app-header">
        <div className="header-container">
          <div className="header-main">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <h1 className="brand-title" style={{ cursor: 'pointer' }} onClick={() => { setSelectedSigungu(''); setSigunguSearch(''); setSearchQuery(''); }}>
                🛡️ Clean Delivery Map
              </h1>
              {selectedSigungu && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--color-text-muted)', flexWrap: 'wrap' }}>
                  <span>📍 {selectedSigungu} (음식점 {shops.length}개)</span>
                  {lastUpdated && (
                    <>
                      <span style={{ opacity: 0.3 }}>|</span>
                      <span>최근 업데이트: {lastUpdated}</span>
                    </>
                  )}
                </div>
              )}
            </div>
            {selectedSigungu && (
              <div className="view-switch">
                <button className={`view-switch-btn ${viewMode === 'list' ? 'active' : ''}`} onClick={() => setViewMode('list')}>📋 리스트</button>
                <button className={`view-switch-btn ${viewMode === 'map' ? 'active' : ''}`} onClick={() => setViewMode('map')}>🗺️ 지도 보기</button>
              </div>
            )}
          </div>

          {selectedSigungu && (
            <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginTop: '16px', alignItems: 'center' }}>
              {/* 시군구 검색창 (헤더 내 배치) */}
              <div ref={dropdownRef} className="search-wrapper" style={{ flex: 1, maxWidth: '300px', position: 'relative' }}>
                <span style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', zIndex: 10 }}>📍</span>
                <input
                  type="text"
                  className="search-input"
                  style={{ paddingLeft: '38px' }}
                  placeholder="시군구 변경..."
                  value={sigunguSearch}
                  onChange={(e) => {
                    setSigunguSearch(e.target.value);
                    setShowDropdown(true);
                  }}
                  onFocus={() => setShowDropdown(true)}
                />
                {showDropdown && (
                  <div style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    marginTop: '8px',
                    background: 'var(--color-card)',
                    border: '1px solid var(--color-border)',
                    borderRadius: '12px',
                    boxShadow: 'var(--glass-shadow)',
                    maxHeight: '220px',
                    overflowY: 'auto',
                    zIndex: 2000,
                  }}>
                    {filteredSigungus.length > 0 ? (
                      filteredSigungus.map((sig, idx) => (
                        <div
                          key={idx}
                          onClick={() => {
                            setSelectedSigungu(sig);
                            setSigunguSearch(sig);
                            setShowDropdown(false);
                          }}
                          style={{
                            padding: '10px 16px',
                            cursor: 'pointer',
                            borderBottom: idx === filteredSigungus.length - 1 ? 'none' : '1px solid rgba(255,255,255,0.03)',
                            transition: 'background 0.2s',
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          {sig}
                        </div>
                      ))
                    ) : (
                      <div style={{ padding: '12px 16px', color: 'var(--color-text-muted)', textAlign: 'center' }}>
                        결과 없음
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* 상점명 또는 주소 검색창 */}
              <div className="search-wrapper" style={{ flex: 1, maxWidth: '300px' }}>
                <input
                  type="text"
                  className="search-input"
                  placeholder="결과 내 매점명/주소 검색..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              {/* 필터 컨트롤 */}
              <div className="filter-container">
                <button className={`filter-btn ${excludeShopInShop ? 'active' : ''}`} onClick={() => setExcludeShopInShop(!excludeShopInShop)}>🚨 샵인샵 제외</button>
                <button className={`filter-btn ${excludeReviewEvent ? 'active' : ''}`} onClick={() => setExcludeReviewEvent(!excludeReviewEvent)}>🎈 리뷰이벤트 제외</button>
              </div>
            </div>
          )}
        </div>
      </header>

      <main className="main-content" style={{ width: '100%', flex: 1, display: 'flex', flexDirection: 'column' }}>
        {!selectedSigungu ? (
          <div className="glass-panel fade-in-up" style={{ padding: '60px 40px', textAlign: 'center', maxWidth: '600px', margin: '80px auto', width: '90%' }}>
            <div style={{ fontSize: '3.5rem', marginBottom: '20px' }}>🔍</div>
            <h2 style={{ fontSize: '1.8rem', marginBottom: '12px', fontWeight: '600', letterSpacing: '-0.5px' }}>시군구를 검색해 주세요</h2>
            <p style={{ color: 'var(--color-text-muted)', marginBottom: '16px', fontSize: '1rem', lineHeight: '1.6' }}>
              청결하고 안전한 배달 매장 정보를 분석해 드립니다.<br />
              원하시는 시군구를 아래 검색창에서 찾아 선택하세요.
            </p>
            {lastUpdated && (
              <p style={{ fontSize: '0.85rem', color: 'var(--color-text-dark)', marginBottom: '35px' }}>
                최근 업데이트: {lastUpdated}
              </p>
            )}
            
            {/* 첫 진입 화면 시군구 검색 인풋 */}
            <div ref={dropdownRef} className="search-wrapper" style={{ position: 'relative', maxWidth: '420px', margin: '0 auto', textAlign: 'left' }}>
              <span style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', fontSize: '1.1rem', zIndex: 10 }}>📍</span>
              <input
                type="text"
                className="search-input"
                style={{ padding: '14px 16px 14px 44px', fontSize: '1rem', background: 'rgba(255, 255, 255, 0.05)' }}
                placeholder="시군구 검색 (예: 강남구, 서초구)..."
                value={sigunguSearch}
                onChange={(e) => {
                  setSigunguSearch(e.target.value);
                  setShowDropdown(true);
                }}
                onFocus={() => setShowDropdown(true)}
              />
              {showDropdown && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  marginTop: '8px',
                  background: 'var(--color-card)',
                  border: '1px solid var(--color-border)',
                  borderRadius: '14px',
                  boxShadow: 'var(--glass-shadow)',
                  maxHeight: '250px',
                  overflowY: 'auto',
                  zIndex: 2000,
                }}>
                  {sigunguLoading ? (
                    <div style={{ padding: '16px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
                      시군구 불러오는 중...
                    </div>
                  ) : filteredSigungus.length > 0 ? (
                    filteredSigungus.map((sig, idx) => (
                      <div
                        key={idx}
                        onClick={() => {
                          setSelectedSigungu(sig);
                          setSigunguSearch(sig);
                          setShowDropdown(false);
                        }}
                        style={{
                          padding: '12px 18px',
                          cursor: 'pointer',
                          borderBottom: idx === filteredSigungus.length - 1 ? 'none' : '1px solid rgba(255,255,255,0.03)',
                          transition: 'background 0.2s',
                          fontSize: '0.95rem',
                        }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.05)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                      >
                        {sig}
                      </div>
                    ))
                  ) : (
                    <div style={{ padding: '16px', color: 'var(--color-text-muted)', textAlign: 'center' }}>
                      일치하는 시군구가 없습니다.
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ) : loading ? (
          <div className="loader-container" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><div className="spinner"></div></div>
        ) : error ? (
          <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', margin: '40px auto', maxWidth: '500px' }}>{error}</div>
        ) : (
          <div className="fade-in-up" style={{ width: '100%' }}>
            {viewMode === 'list' ? (
              <ShopList shops={filteredShops} />
            ) : (
              <Map shops={filteredShops} />
            )}
          </div>
        )}
      </main>
    </div>
  );
};

export default DashboardContainer;
