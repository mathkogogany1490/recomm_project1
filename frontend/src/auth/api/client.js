import axios from "axios";
import { tokenStorage } from "./token";

export const apiClient = axios.create({
    baseURL: "/api",
    timeout: 10000,
    headers: {
        "Content-Type": "application/json",
    },
});

apiClient.interceptors.request.use((config) => {
    const token = tokenStorage.get();

    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
});

export function getApiError(error) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
        return detail;
    }

    if (Array.isArray(detail)) {
        return detail
            .map((item) => item.msg || "입력값을 확인해 주세요.")
            .join("\n");
    }

    const message = error.response?.data?.message;

    if (typeof message === "string") {
        return message;
    }

    if (error.code === "ECONNABORTED") {
        return "서버 응답 시간이 초과되었습니다.";
    }

    if (!error.response) {
        return "서버에 연결할 수 없습니다.";
    }

    return `요청에 실패했습니다. (${error.response.status})`;
}