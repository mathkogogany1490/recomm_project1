import { Outlet } from "react-router-dom";
import styled from "styled-components";

import HeaderBar from "./HeaderBar";
import SideBar from "./SideBar";

const Container = styled.div`
  min-height: 100vh;
  background: #f5f7fb;
`;

const Body = styled.div`
  display: flex;
  min-height: calc(100vh - 64px);
`;

const Content = styled.main`
  flex: 1;
  min-width: 0;
  padding: 32px;
`;

export default function AppLayout() {
    return (
        <Container>
            <HeaderBar />

            <Body>
                <SideBar />

                <Content>
                    <Outlet />
                </Content>
            </Body>
        </Container>
    );
}