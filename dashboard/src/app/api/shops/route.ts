import { NextResponse } from 'next/server';
import { Pool } from 'pg';

// 전역 자원 누수를 방지하기 위해 단일 Pool 인스턴스를 유지합니다.
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL?.includes('supabase.com') ? { rejectUnauthorized: false } : undefined,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 15000,
});

export async function GET() {
  let client;
  try {
    client = await pool.connect();

    const query = `
      SELECT 
        r.*, 
        s.company_name AS raw_company_name 
      FROM refined_shops r
      LEFT JOIN shops s ON r.id = s.id
      LIMIT 100
    `;

    const queryResult = await client.query(query);

    const shops = queryResult.rows.map(shop => {
      return {
        id: shop.id,
        name: shop.name,
        company_name: shop.raw_company_name || null,
        address: shop.address,
        detailed_address: shop.detailed_address,
        building_name: shop.building_name,
        floor: shop.floor,
        room_number: shop.room_number,
        raw_rating: parseFloat(shop.raw_rating) || 0,
        review_count: parseInt(shop.review_count, 10) || 0,
        has_review_event: shop.has_review_event || false,
        is_shop_in_shop: shop.is_shop_in_shop || false,
        is_suspicious: shop.is_suspicious || false,
        sis_group_id: shop.sis_group_id,
        sis_sibling_count: parseInt(shop.sis_sibling_count, 10) || 0,
        sis_sibling_names: shop.sis_sibling_names,
        external_metadata: shop.external_metadata,
        latitude: parseFloat(shop.lat) || 37.5665,
        longitude: parseFloat(shop.lng) || 126.9780,
      };
    });

    return NextResponse.json(shops);
  } catch (error) {
    console.error('Error occurred in API router (/api/shops):', error);
    return NextResponse.json(
      { error: 'Internal Server Error', details: error instanceof Error ? error.message : String(error) },
      { status: 500 }
    );
  } finally {
    if (client) {
      client.release(); // 💎 안전하게 풀로 자원을 반납합니다.
    }
  }
}