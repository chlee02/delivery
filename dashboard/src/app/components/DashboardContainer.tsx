"use client";
import React, { useEffect, useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import ShopList from './ShopList';

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
};

const DashboardContainer: React.FC = () => {
  const [shops, setShops] = useState<Shop[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [excludeShopInShop, setExcludeShopInShop] = useState<boolean>(false);
  const [excludeReviewEvent, setExcludeReviewEvent] = useState<boolean>(false);

  useEffect(() => {
    const fetchShops = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/shops');
        const data = await response.json();
        setShops(Array.isArray(data) ? data : []);
      } catch (err) {
        setError('데이터를 불러오는 중 문제가 발생했습니다.');
      } finally {
        setLoading(false);
      }
    };
    fetchShops();
  }, []);

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
            <h1 className="brand-title">🛡️ Clean Delivery Map</h1>
            <div className="view-switch">
              <button className={`view-switch-btn ${viewMode === 'list' ? 'active' : ''}`} onClick={() => setViewMode('list')}>📋 리스트</button>
              <button className={`view-switch-btn ${viewMode === 'map' ? 'active' : ''}`} onClick={() => setViewMode('map')}>🗺️ 지도 보기</button>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginTop: '16px' }}>
            <div className="search-wrapper" style={{ flex: 1, maxWidth: '400px' }}>
              <input 
                type="text" 
                className="search-input" 
                placeholder="상점명 또는 주소 검색..." 
                value={searchQuery} 
                onChange={(e) => setSearchQuery(e.target.value)} 
              />
            </div>
            <div className="filter-container">
              <button className={`filter-btn ${excludeShopInShop ? 'active' : ''}`} onClick={() => setExcludeShopInShop(!excludeShopInShop)}>🚨 샵인샵 제외</button>
              <button className={`filter-btn ${excludeReviewEvent ? 'active' : ''}`} onClick={() => setExcludeReviewEvent(!excludeReviewEvent)}>🎈 리뷰이벤트 제외</button>
            </div>
          </div>
        </div>
      </header>

      <main className="main-content" style={{ width: '100%' }}>
        {loading ? (
          <div className="loader-container"><div className="spinner"></div></div>
        ) : error ? (
          <div className="glass-panel" style={{ padding: '40px', textAlign: 'center' }}>{error}</div>
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
