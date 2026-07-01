import { NextResponse } from 'next/server';
import { Pool } from 'pg';
import fs from 'fs';
import path from 'path';

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
      SELECT DISTINCT law_address_sigungu 
      FROM shops 
      WHERE law_address_sigungu IS NOT NULL AND law_address_sigungu != ''
      ORDER BY law_address_sigungu
    `;

    const queryResult = await client.query(query);
    const sigungus = queryResult.rows.map(row => row.law_address_sigungu);

    let lastUpdated = '';
    
    // DB의 system_metadata 테이블 조회 시도
    try {
      const metaResult = await client.query(
        "SELECT value FROM system_metadata WHERE key = 'last_updated'"
      );
      if (metaResult.rows.length > 0) {
        lastUpdated = metaResult.rows[0].value;
      }
    } catch (metaErr) {
      console.warn('system_metadata 테이블 조회 실패, 파일 대안 사용:', metaErr);
    }

    // DB 조회 실패 또는 결과가 없으면 last_updated.txt 파일에서 대안 조회
    if (!lastUpdated) {
      try {
        const filePath = path.join(process.cwd(), '..', 'last_updated.txt');
        if (fs.existsSync(filePath)) {
          lastUpdated = fs.readFileSync(filePath, 'utf-8').trim();
        } else {
          const localPath = path.join(process.cwd(), 'last_updated.txt');
          if (fs.existsSync(localPath)) {
            lastUpdated = fs.readFileSync(localPath, 'utf-8').trim();
          }
        }
      } catch (fsErr) {
        console.error('last_updated.txt 파일 읽기 실패:', fsErr);
      }
    }

    return NextResponse.json({
      sigungus,
      lastUpdated
    });
  } catch (error) {
    console.error('Error occurred in API router (/api/sigungu):', error);
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
