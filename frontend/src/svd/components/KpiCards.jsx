import { Row, Col, Card, Statistic, Alert, Spin } from "antd";
import styled from "styled-components";

import { useSvdKpi } from "../query/useSvd";
import { getApiError } from "../../auth/api/client";

const KpiContainer = styled.div`
  margin-bottom: 28px;
`;

export default function KpiCards() {
    const { data, isLoading, error } = useSvdKpi();

    if (isLoading) {
        return (
            <KpiContainer>
                <Spin />
            </KpiContainer>
        );
    }

    if (error) {
        return (
            <KpiContainer>
                <Alert
                    type="error"
                    title="SVD 평가 지표 조회 실패"
                    description={getApiError(error)}
                    showIcon
                />
            </KpiContainer>
        );
    }

    const items = [
        {
            title: "MAE",
            value: data.mae,
            description: "평균 절대 오차",
        },
        {
            title: "MSE",
            value: data.mse,
            description: "평균 제곱 오차",
        },
        {
            title: "RMSE",
            value: data.rmse,
            description: "평균 제곱근 오차",
        },
    ];

    return (
        <KpiContainer>
            <Row gutter={[16, 16]}>
                {items.map((item) => (
                    <Col xs={24} sm={8} key={item.title}>
                        <Card>
                            <Statistic
                                title={item.title}
                                value={item.value}
                                precision={4}
                                valueStyle={{
                                    color: "#1677ff",
                                    fontWeight: 700,
                                }}
                            />

                            <div
                                style={{
                                    marginTop: 8,
                                    color: "#888",
                                    fontSize: 12,
                                }}
                            >
                                {item.description}
                            </div>
                        </Card>
                    </Col>
                ))}
            </Row>

            {data.evaluation === "training" && (
                <div
                    style={{
                        marginTop: 10,
                        fontSize: 12,
                        color: "#888",
                    }}
                >
                    * 학습 데이터 기준 평가 지표입니다.
                </div>
            )}
        </KpiContainer>
    );
}