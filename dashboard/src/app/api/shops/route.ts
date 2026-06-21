import { NextResponse } from 'next/server';
import { Pool } from 'pg';

// Create a single client pool that will be reused across requests
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL?.includes('supabase.com') ? { rejectUnauthorized: false } : undefined,
  max: 10, // Limit maximum connections in the pool
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

export async function GET() {
  let client;
  try {
    client = await pool.connect();
    
    // Retrieve refined shops, prioritizing raw ratings
    const queryResult = await client.query('SELECT * FROM refined_shops ORDER BY raw_rating DESC');
    
    // Map DB rows to API response objects
    const shops = queryResult.rows.map(shop => {
      return {
        id: shop.id,
        name: shop.name,
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
      client.release();
    }
  }
}
