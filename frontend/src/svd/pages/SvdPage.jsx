import { useState } from "react";
import {
    Typography,
    Card,
    InputNumber,
    Button,
    Space,
    Alert,
} from "antd";

import styled from "styled-components";

import { SearchOutlined } from "@ant-design/icons";

import KpiCards from "../components/KpiCards";
import RecommendationTable from "../components/RecommendationTable";

import { useSvdRecommendations } from "../query/useSvd";
import { getApiError } from "../../auth/api/client";

const { Title, Paragraph } = Typography;

const Container = styled.div`
  max-width: 1200px;
  margin: 0 auto;
`;

const SearchArea = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
`;

export default function SvdPage() {
    const [inputUserId, setInputUserId] = useState(1);
    const [selectedUserId, setSelectedUserId] = useState(null);

    const {
        data,
        isLoading,
        error,
    } = useSvdRecommendations(selectedUserId);

    const handleSearch = () => {
        if (
            !Number.isSafeInteger(inputUserId) ||
            inputUserId <= 0
        ) {
            return;
        }

        setSelectedUserId(inputUserId);
    };

    return (
        <Container>
            <Title level={2}>SVD 영화 추천</Title>

            <Paragraph type="secondary">
                희소 행렬 기반 SVD로 사용자별 영화 평점을
                예측하고 추천합니다.
            </Paragraph>

            <KpiCards />

            <Card
                title="사용자별 영화 추천"
                style={{ marginTop: 24 }}
            >
                <SearchArea>
                    <InputNumber
                        min={1}
                        max={Number.MAX_SAFE_INTEGER}
                        precision={0}
                        value={inputUserId}
                        onChange={setInputUserId}
                        placeholder="고객 ID"
                        style={{ width: 200 }}
                        size="large"
                    />

                    <Button
                        type="primary"
                        size="large"
                        icon={<SearchOutlined />}
                        onClick={handleSearch}
                        disabled={
                            !Number.isSafeInteger(inputUserId) ||
                            inputUserId <= 0
                        }
                        loading={isLoading}
                    >
                        추천 조회
                    </Button>
                </SearchArea>

                {error && (
                    <Alert
                        type="error"
                        title="추천 조회 실패"
                        description={getApiError(error)}
                        showIcon
                        style={{ marginBottom: 20 }}
                    />
                )}

                {data && (
                    <Paragraph>
                        고객 <strong>{data.user_id}</strong>님의
                        미평가 영화 추천 결과입니다.
                    </Paragraph>
                )}

                <RecommendationTable
                    recommendations={error ? [] : data?.recommendations || []}
                    loading={isLoading}
                />
            </Card>
        </Container>
    );
}