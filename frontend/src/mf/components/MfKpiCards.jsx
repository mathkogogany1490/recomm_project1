import {
    Row,
    Col,
    Card,
    Statistic,
    Alert,
    Spin,
    Typography,
} from "antd";

import { useMfKpi } from "../query/useMf";

const { Text } = Typography;

export default function MfKpiCards() {
    const { data, isLoading, error } = useMfKpi();

    if (isLoading) {
        return <Spin />;
    }

    if (error) {
        return (
            <Alert
                type="error"
                title="MF 평가 지표 조회 실패"
                description={
                    error.response?.data?.detail ||
                    error.message
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
                    검증 데이터 기준 · 학습 {data.train_count.toLocaleString()}건
                    {" · "}
                    검증 {data.validation_count.toLocaleString()}건
                    {" · "}
                    최적 Epoch {data.epochs}
                    {" · "}
                    현재 장치 {data.device.toUpperCase()}
                </Text>
            </div>
        </div>
    );
}