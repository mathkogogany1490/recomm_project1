import { apiClient } from "../../auth/api/client";

export const mfApi = {
    async getKpi() {
        const response = await apiClient.get("/mf/kpi");
        return response.data;
    },

    async getRecommendations(userId) {
        const response = await apiClient.get(
            "/mf/recommendations",
            {
                params: {
                    user_id: userId,
                },
            }
        );

        return response.data;
    },
};