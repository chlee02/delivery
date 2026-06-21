import type { Metadata } from "next";
import "leaflet/dist/leaflet.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "🛡️ Clean Delivery Map | 위장 가맹점 및 리뷰 분석 대시보드",
  description: "요기요 수집 데이터를 바탕으로 배달앱 내 샵인샵(위장 가맹점) 식별 정보와 리뷰 이벤트 평점 보정 신뢰도 스코어를 시각화해 주는 프리미엄 대시보드입니다.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <head>
        {/* Modern font imports */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body>
        {children}
      </body>
    </html>
  );
}
