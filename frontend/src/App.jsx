import { useEffect, useState } from "react";
import { Layout } from "antd";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import SideBar from "./auth/components/SideBar";
import HeaderBar from "./auth/components/HeaderBar";

import MemberPage from "./auth/pages/MemberPage";
import SvdPage from "./svd/pages/SvdPage";
import MfPage from "./mf/pages/MfPage";
import TransformerPage from "./transformer/pages/TransformerPage";

import { getToken } from "./api/client";

const { Content } = Layout;

function AppLayout() {
  const [isLoggedIn, setIsLoggedIn] = useState(
    Boolean(getToken())
  );

  useEffect(() => {
    const updateAuth = () => {
      setIsLoggedIn(Boolean(getToken()));
    };

    window.addEventListener("auth-changed", updateAuth);
    window.addEventListener("storage", updateAuth);

    return () => {
      window.removeEventListener("auth-changed", updateAuth);
      window.removeEventListener("storage", updateAuth);
    };
  }, []);

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <SideBar isLoggedIn={isLoggedIn} />

      <Layout>
        <HeaderBar
          isLoggedIn={isLoggedIn}
        />

        <Content
          style={{
            margin: 24,
            padding: 24,
            background: "#fff",
            borderRadius: 8,
            minHeight: 400,
          }}
        >
          <Routes>
            <Route
              path="/"
              element={<Navigate to="/member" replace />}
            />

            <Route
              path="/member"
              element={<MemberPage />}
            />

            {isLoggedIn && (
              <>
                <Route
                  path="/svd"
                  element={<SvdPage />}
                />

                <Route
                  path="/mf"
                  element={<MfPage />}
                />

                <Route
                  path="/transformer"
                  element={<TransformerPage />}
                />
              </>
            )}

            <Route
              path="*"
              element={<Navigate to="/member" replace />}
            />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}