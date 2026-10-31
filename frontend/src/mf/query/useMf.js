import { useQuery } from "@tanstack/react-query";

import { mfApi } from "../api/mfApi";


export function useMfKpi() {
    return useQuery({
        queryKey: ["mf", "kpi"],
        queryFn: mfApi.getKpi,
        staleTime: 5 * 60 * 1000,
        retry: false,
    });
}


export function useMfRecommendations(userId) {
    return useQuery({
        queryKey: ["mf", "recommendations", userId],
        queryFn: () => mfApi.getRecommendations(userId),
        enabled: Number.isSafeInteger(userId) && userId > 0,
        staleTime: 60 * 1000,
        retry: false,
    });
}