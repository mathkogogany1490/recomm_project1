import {
    Card,
    Typography,
    Descriptions,
    Alert,
    Spin,
    Empty,
    Tag,
} from "antd";

import { UserOutlined } from "@ant-design/icons";
import styled from "styled-components";

import { useAuth, useMe } from "../query/useAuth";
import { getApiError } from "../api/client";

const { Title, Paragraph } = Typography;

const PageContainer = styled.div`
  max-width: 900px;
  margin: 0 auto;
`;

const PageTitle = styled.div`
  margin-bottom: 24px;
`;

export default function MemberPage() {
    const { isAuthenticated } = useAuth();
    const { data: user, isLoading, error } = useMe();

    if (!isAuthenticated) {
        return (
            <PageContainer>
                <PageTitle>
                    <Title level={2}>회원</Title>
                    <Paragraph type="secondary">
                        회원 정보를 관리하는 페이지입니다.
                    </Paragraph>
                </PageTitle>

                <Card>
                    <Empty
                        image={<UserOutlined style={{ fontSize: 48 }} />}
                        description="로그인이 필요합니다."
                    >
                        상단의 로그인 또는 회원가입 버튼을 이용해 주세요.
                    </Empty>
                </Card>
            </PageContainer>
        );
    }

    return (
        <PageContainer>
            <PageTitle>
                <Title level={2}>내 정보</Title>
                <Paragraph type="secondary">
                    회원 계정 정보를 확인할 수 있습니다.
                </Paragraph>
            </PageTitle>

            <Card title="회원 정보">
                {isLoading ? (
                    <div style={{ textAlign: "center", padding: 40 }}>
                        <Spin size="large" />
                    </div>
                ) : error ? (
                    <Alert
                        type="error"
                        title="회원 정보를 불러오지 못했습니다."
                        description={getApiError(error)}
                        showIcon
                    />
                ) : user ? (
                    <Descriptions
                        bordered
                        column={1}
                        labelStyle={{ width: 160 }}
                    >
                        <Descriptions.Item label="회원 번호">
                            {user.id}
                        </Descriptions.Item>

                        <Descriptions.Item label="이메일">
                            {user.email}
                        </Descriptions.Item>

                        <Descriptions.Item label="이메일 인증">
                            {user.is_verified ? (
                                <Tag color="success">인증 완료</Tag>
                            ) : (
                                <Tag color="warning">미인증</Tag>
                            )}
                        </Descriptions.Item>
                    </Descriptions>
                ) : (
                    <Empty description="회원 정보가 없습니다." />
                )}
            </Card>
        </PageContainer>
    );
}