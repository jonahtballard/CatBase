// frontend/src/AppRouter.jsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import NavBar from "./components/NavBar";
import App from "./App.jsx";        // Home (shows current term only)
import Past from "./pages/Past.jsx"; // New explorer 

export default function AppRouter() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/past" element={<Past />} />
      </Routes>
    </BrowserRouter>
  );
}
