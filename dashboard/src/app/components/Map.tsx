"use client";
import React, { useEffect, useRef, useMemo } from 'react';
import * as L from 'leaflet';

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

interface Props {
  shops: Shop[];
}

const SEOUL_CENTER: [number, number] = [37.5025, 127.0435];

const Map: React.FC<Props> = ({ shops }) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

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

  const renderMarkers = (map: L.Map, layer: L.LayerGroup, data: Shop[]) => {
    layer.clearLayers();
    data.forEach(shop => {
      let color = 'hsl(220, 85%, 58%)';
      if (shop.is_shop_in_shop) color = 'hsl(355, 85%, 58%)';
      else if (shop.has_review_event) color = 'hsl(42, 100%, 53%)';

      const icon = L.divIcon({
        html: `
          <div style="position:relative;width:24px;height:24px;display:flex;align-items:center;justify-content:center;">
            <div style="position:absolute;width:20px;height:20px;border-radius:50%;background:${color};opacity:0.2;animation:pulse 2s infinite alternate;"></div>
            <div style="width:10px;height:10px;border-radius:50%;background:${color};border:2px solid #fff;shadow:0 0 8px ${color};"></div>
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
        <div style="min-width:180px;color:#fff;">
          <h3 style="margin:0 0 4px 0;font-size:0.95rem;font-weight:800;">${shop.name}</h3>
          <p style="margin:0 0 2px 0;font-size:0.75rem;color:#ccc;">${shop.address}</p>
          <p style="margin:0 0 8px 0;font-size:0.7rem;color:#888;">${fullDetail}</p>
          <div style="border-top:1px solid rgba(255,255,255,0.1);padding-top:8px;font-weight:800;color:#f59e0b;">⭐ ${shop.raw_rating.toFixed(1)}</div>
        </div>
      `;

      L.marker([shop.latitude, shop.longitude], { icon }).bindPopup(popupContent).addTo(layer);
    });
  };

  useEffect(() => {
    if (!mapRef.current) return;

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

    // Force multiple re-renders to ensure width is caught
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
  }, []);

  useEffect(() => {
    if (mapInstanceRef.current && markersLayerRef.current) {
      renderMarkers(mapInstanceRef.current, markersLayerRef.current, distributedShops);
      mapInstanceRef.current.setView(mapCenter);
      mapInstanceRef.current.invalidateSize();
    }
  }, [distributedShops, mapCenter]);

  return (
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
  );
};

export default Map;
