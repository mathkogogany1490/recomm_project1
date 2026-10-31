import { useState } from "react";

import {
    Typography,
    Card,
    InputNumber,
    Button,
    Alert,
} from "antd";

import { SearchOutlined } from "@ant-design/icons";
import styled from "styled-components";

import MfKpiCards from "../components/MfKpiCards";
import MfRecommendationTable from "../components/MfRecommendationTable";
import { useMfRecommendations } from "../query/useMf";


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


export default function MfPage() {
    const [inputUserId, setInputUserId] = useState(1);
    const [selectedUserId, setSelectedUserId] = useState(null);

    const {
        data,
        isLoading,
        error,
    } = useMfRecommendations(selectedUserId);

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
            <Title level={2}>MF 영화 추천</Title>

            <Paragraph type="secondary">
                사용자 벡터와 영화 벡터의 내적으로
                평점을 예측하는 Matrix Factorization 추천 시스템입니다.
            </Paragraph>

            <MfKpiCards />

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
                        description={
                            error.response?.data?.detail ||
                            error.message
                        }
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

                <MfRecommendationTable
                    recommendations={
                        error ? [] : data?.recommendations || []
                    }
                    loading={isLoading}
                />
            </Card>
        </Container>
    );
}