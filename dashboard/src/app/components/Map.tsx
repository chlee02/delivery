"use client";
import React, { useEffect, useRef, useMemo, useState } from 'react';

// 💡 중요: Next.js 서버 사이드 에러를 방지하기 위해 window 객체가 있을 때만 leaflet을 가져옵니다.
let L: any = null;
if (typeof window !== 'undefined') {
  L = require('leaflet');
}

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

interface Props {
  shops: Shop[];
}

const SEOUL_CENTER: [number, number] = [37.5025, 127.0435];

const Map: React.FC<Props> = ({ shops }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersLayerRef = useRef<any>(null);
  const [isMounted, setIsMounted] = useState(false);

  // 컴포넌트가 브라우저에 마운트되었는지 확인 (SSR 우회용)
  useEffect(() => {
    setIsMounted(true);
  }, []);

  const mapCenter = useMemo(() => {
    if (shops.length === 0) return SEOUL_CENTER;
    const totalLat = shops.reduce((sum, s) => sum + s.latitude, 0);
    const totalLng = shops.reduce((sum, s) => sum + s.longitude, 0);
    return [totalLat / shops.length, totalLng / shops.length] as [number, number];
  }, [shops]);

  const distributedShops = useMemo(() => {
    const coordsMap: { [key: string]: Shop[] } = {};
    shops.forEach(shop => {
      const key = `${shop.latitude.toFixed(5)},${shop.longitude.toFixed(5)}`;
      if (!coordsMap[key]) coordsMap[key] = [];
      coordsMap[key].push(shop);
    });

    const result: Shop[] = [];
    Object.keys(coordsMap).forEach(key => {
      const group = coordsMap[key];
      if (group.length === 1) result.push(group[0]);
      else {
        const radius = 0.00018;
        group.forEach((shop, index) => {
          const angle = (2 * Math.PI * index) / group.length;
          result.push({
            ...shop,
            latitude: shop.latitude + radius * Math.cos(angle),
            longitude: shop.longitude + radius * Math.sin(angle)
          });
        });
      }
    });
    return result;
  }, [shops]);

  const renderMarkers = (map: any, layer: any, data: Shop[]) => {
    if (!L) return;
    layer.clearLayers();
    data.forEach(shop => {
      let color = 'hsl(220, 85%, 58%)';
      if (shop.is_shop_in_shop) color = 'hsl(355, 85%, 58%)';
      else if (shop.has_review_event) color = 'hsl(42, 100%, 53%)';

      const icon = L.divIcon({
        html: `
          <div style="position:relative;width:24px;height:24px;display:flex;align-items:center;justify-content:center;">
            <div style="position:absolute;width:20px;height:20px;border-radius:50%;background:${color};opacity:0.2;"></div>
            <div style="width:10px;height:10px;border-radius:50%;background:${color};border:2px solid #fff;box-shadow:0 0 8px ${color};"></div>
          </div>
        `,
        className: 'custom-neon-marker',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -12]
      });

      const fullDetail = [
        shop.detailed_address,
        shop.building_name,
        shop.floor,
        shop.room_number
      ].filter(Boolean).join(' ');

      const popupContent = `
        <div style="min-width:180px;color:#111;padding:5px;">
          <h3 style="margin:0 0 4px 0;font-size:0.95rem;font-weight:800;color:#000;">${shop.name}</h3>
          <p style="margin:0 0 2px 0;font-size:0.75rem;color:#555;">${shop.address}</p>
          <p style="margin:0 0 8px 0;font-size:0.7rem;color:#777;">${fullDetail}</p>
          <div style="border-top:1px solid rgba(0,0,0,0.1);padding-top:8px;font-weight:800;color:#f59e0b;">⭐ ${shop.raw_rating.toFixed(1)}</div>
        </div>
      `;

      L.marker([shop.latitude, shop.longitude], { icon }).bindPopup(popupContent).addTo(layer);
    });
  };

  useEffect(() => {
    if (!isMounted || !mapRef.current || !L) return;

    // Standard Leaflet Init
    const map = L.map(mapRef.current, {
      zoomControl: true,
      fadeAnimation: true
    }).setView(mapCenter, 14);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const markersLayer = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    markersLayerRef.current = markersLayer;

    renderMarkers(map, markersLayer, distributedShops);

    const timer1 = setTimeout(() => map.invalidateSize(), 100);
    const timer2 = setTimeout(() => map.invalidateSize(), 500);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [isMounted]);

  useEffect(() => {
    if (mapInstanceRef.current && markersLayerRef.current) {
      renderMarkers(mapInstanceRef.current, markersLayerRef.current, distributedShops);
      mapInstanceRef.current.setView(mapCenter);
      mapInstanceRef.current.invalidateSize();
    }
  }, [distributedShops, mapCenter]);

  // 브라우저에 마운트되기 전에는 빈 컨테이너만 보여줍니다.
  if (!isMounted) {
    return <div style={{ height: '650px', width: '100%', background: '#111', borderRadius: '20px' }} />;
  }

  return (
    <>
      {/* 💡 Leaflet 스타일시트 에러를 해결하기 위해 공식 CDN 스타일을 직접 주입합니다. */}
      <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
        crossOrigin=""
      />

      <div
        ref={mapRef}
        className="map-container-wrapper leaflet-container"
        style={{
          height: '650px',
          width: '100%',
          minWidth: '100%',
          display: 'block',
          background: '#111',
          borderRadius: '20px',
          overflow: 'hidden',
          position: 'relative'
        }}
      />
    </>
  );
};

export default Map;