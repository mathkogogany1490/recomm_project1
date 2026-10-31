import {
    Table,
    Tag,
    Rate,
    Space,
    Typography,
} from "antd";

const { Text } = Typography;

export default function MfRecommendationTable({
                                                  recommendations = [],
                                                  loading = false,
                                              }) {
    const columns = [
        {
            title: "순위",
            dataIndex: "rank",
            key: "rank",
            width: 80,
            align: "center",
            render: (value) => <Text strong>{value}</Text>,
        },
        {
            title: "영화 ID",
            dataIndex: "movie_id",
            key: "movie_id",
            width: 110,
        },
        {
            title: "영화 제목",
            dataIndex: "title",
            key: "title",
            render: (value) => <Text strong>{value}</Text>,
        },
        {
            title: "장르",
            dataIndex: "genres",
            key: "genres",
            render: (genres) => (
                <Space size={[4, 4]} wrap>
                    {genres.map((genre) => (
                        <Tag key={genre} color="blue">
                            {genre}
                        </Tag>
                    ))}
                </Space>
            ),
        },
        {
            title: "예측 평점",
            dataIndex: "predicted_rating",
            key: "predicted_rating",
            width: 220,
            render: (rating) => (
                <Space>
                    <Rate
                        disabled
                        allowHalf
                        value={Math.round(rating * 2) / 2}
                        style={{ fontSize: 14 }}
                    />

                    <Text strong>
                        {rating.toFixed(2)}
                    </Text>
                </Space>
            ),
        },
    ];

    return (
        <Table
            rowKey="movie_id"
            columns={columns}
            dataSource={recommendations}
            loading={loading}
            pagination={false}
            scroll={{ x: 800 }}
            locale={{
                emptyText: "추천 결과가 없습니다.",
            }}
        />
    );
}