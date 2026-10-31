import { apiClient } from "../../auth/api/client";

export const transformerApi = {
    async getKpi() {
        const response = await apiClient.get(
            "/transformer/kpi"
        );

        return response.data;
    },

    async getRecommendations(userId) {
        const response = await apiClient.get(
            "/transformer/recommendations",
            {
                params: {
                    user_id: userId,
                },
            }
        );

        return response.data;
    },
};