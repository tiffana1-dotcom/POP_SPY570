import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/AppLayout";
import { Dashboard } from "@/pages/Dashboard";
import { ProductAlertDetail } from "@/pages/ProductAlertDetail";
import { WatchlistPage } from "@/pages/WatchlistPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="watchlist" element={<WatchlistPage />} />
        <Route path="products/:id" element={<ProductAlertDetail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
