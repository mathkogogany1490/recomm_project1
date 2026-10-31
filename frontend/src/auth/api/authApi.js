import { apiClient } from "./client";

export const authApi = {
    async signup(data) {
        const response = await apiClient.post("/users", data);
        return response.data;
    },

    async verifyEmail(data) {
        const response = await apiClient.post(
            "/auth/verify-email",
            data
        );
        return response.data;
    },

    async resendCode(email) {
        const response = await apiClient.post(
            "/auth/resend-code",
            { email }
        );
        return response.data;
    },

    async login(data) {
        const response = await apiClient.post(
            "/auth/login",
            data
        );
        return response.data;
    },

    async getMe() {
        const response = await apiClient.get("/users/me");
        return response.data;
    },
};