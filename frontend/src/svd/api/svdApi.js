import { apiClient } from "../../auth/api/client";

export const svdApi = {
    async getKpi() {
        const response = await apiClient.get("/svd/kpi");
        return response.data;
    },

    async getRecommendations(userId) {
        const response = await apiClient.get(
            "/svd/recommendations",
            {
                params: {
                    user_id: userId,
                },
            }
        );

        return response.data;
    },
};