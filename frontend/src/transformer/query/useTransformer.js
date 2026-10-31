import { useQuery } from "@tanstack/react-query";

import { transformerApi } from "../api/transformerApi";


export function useTransformerKpi() {
    return useQuery({
        queryKey: ["transformer", "kpi"],
        queryFn: transformerApi.getKpi,
        staleTime: 5 * 60 * 1000,
        retry: false,
    });
}


export function useTransformerRecommendations(userId) {
    return useQuery({
        queryKey: [
            "transformer",
            "recommendations",
            userId,
        ],
        queryFn: () =>
            transformerApi.getRecommendations(userId),
        enabled: Number.isSafeInteger(userId) && userId > 0,
        staleTime: 60 * 1000,
        retry: false,
    });
}