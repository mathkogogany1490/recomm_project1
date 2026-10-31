import { Layout, Menu } from "antd";
import {
  UserOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  RobotOutlined,
} from "@ant-design/icons";

import {
  useLocation,
  useNavigate,
} from "react-router-dom";

const { Sider } = Layout;

export default function SideBar({ isLoggedIn }) {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: "/member",
      icon: <UserOutlined />,
      label: "회원",
    },

    ...(isLoggedIn
      ? [
          {
            key: "/svd",
            icon: <DatabaseOutlined />,
            label: "SVD 추천",
          },
          {
            key: "/mf",
            icon: <BarChartOutlined />,
            label: "MF 추천",
          },
          {
            key: "/transformer",
            icon: <RobotOutlined />,
            label: "Transformer 추천",
          },
        ]
      : []),
  ];

  const selectedKey =
    menuItems.find(
      (item) =>
        location.pathname === item.key ||
        location.pathname.startsWith(`${item.key}/`)
    )?.key || "/member";

  return (
    <Sider
      width={230}
      breakpoint="lg"
      collapsedWidth="0"
      style={{
        minHeight: "100vh",
      }}
    >
      <div
        style={{
          height: 64,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#fff",
          fontSize: 18,
          fontWeight: 700,
        }}
      >
        추천 시스템
      </div>

      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
      />
    </Sider>
  );
}