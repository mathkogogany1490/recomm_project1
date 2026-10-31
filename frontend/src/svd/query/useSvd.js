import { useQuery } from "@tanstack/react-query";

import { svdApi } from "../api/svdApi";

export function useSvdKpi() {
    return useQuery({
        queryKey: ["svd", "kpi"],
        queryFn: svdApi.getKpi,
        retry: false,
        staleTime: 5 * 60 * 1000,
    });
}

export function useSvdRecommendations(userId) {
    return useQuery({
        queryKey: ["svd", "recommendations", userId],
        queryFn: () => svdApi.getRecommendations(userId),
        enabled: Number.isSafeInteger(userId) && userId > 0,
        retry: false,
        staleTime: 60 * 1000,
    });
}