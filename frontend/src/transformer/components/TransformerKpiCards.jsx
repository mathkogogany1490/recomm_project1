import {
    Row,
    Col,
    Card,
    Statistic,
    Alert,
    Spin,
    Typography,
} from "antd";

import { useTransformerKpi } from "../query/useTransformer";

const { Text } = Typography;


export default function TransformerKpiCards() {
    const { data, isLoading, error } = useTransformerKpi();

    if (isLoading) {
        return <Spin />;
    }

    if (error) {
        return (
            <Alert
                type="error"
                title="Transformer 평가 지표 조회 실패"
                description={
                    typeof error.response?.data?.detail === "string"
                        ? error.response.data.detail
                        : error.message
                }
                showIcon
            />
        );
    }

    const metrics = [
        {
            key: "mae",
            title: "MAE",
            description: "평균 절대 오차",
        },
        {
            key: "mse",
            title: "MSE",
            description: "평균 제곱 오차",
        },
        {
            key: "rmse",
            title: "RMSE",
            description: "평균 제곱근 오차",
        },
    ];

    return (
        <div style={{ marginBottom: 28 }}>
            <Row gutter={[16, 16]}>
                {metrics.map((metric) => (
                    <Col xs={24} sm={8} key={metric.key}>
                        <Card>
                            <Statistic
                                title={metric.title}
                                value={data[metric.key]}
                                precision={4}
                                valueStyle={{
                                    color: "#1677ff",
                                    fontWeight: 700,
                                }}
                            />

                            <Text type="secondary">
                                {metric.description}
                            </Text>
                        </Card>
                    </Col>
                ))}
            </Row>

            <div style={{ marginTop: 12 }}>
                <Text type="secondary">
                    검증 구간 기준
                    {" · "}
                    학습 {data.train_count.toLocaleString()}건
                    {" · "}
                    검증 {data.validation_count.toLocaleString()}건
                    {" · "}
                    최적 Epoch {data.epochs}
                </Text>
            </div>
        </div>
    );
}