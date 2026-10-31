import {
  Layout,
  Button,
  Space,
  Typography,
} from "antd";

import {
  LoginOutlined,
  LogoutOutlined,
} from "@ant-design/icons";

import { useNavigate } from "react-router-dom";

import { clearToken } from "../../api/client";

const { Header } = Layout;

export default function HeaderBar({ isLoggedIn }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearToken();
    navigate("/member", { replace: true });
  };

  return (
    <Header
      style={{
        background: "#fff",
        padding: "0 24px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderBottom: "1px solid #f0f0f0",
      }}
    >
      <Typography.Text strong>
        영화 추천 서비스
      </Typography.Text>

      <Space>
        <Typography.Text type="secondary">
          {isLoggedIn ? "로그인 상태" : "로그아웃 상태"}
        </Typography.Text>

        {isLoggedIn ? (
          <Button
            icon={<LogoutOutlined />}
            onClick={handleLogout}
          >
            로그아웃
          </Button>
        ) : (
          <Button
            type="primary"
            icon={<LoginOutlined />}
            onClick={() => navigate("/member")}
          >
            로그인
          </Button>
        )}
      </Space>
    </Header>
  );
}