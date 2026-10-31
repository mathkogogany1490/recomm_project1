import {
    createContext,
    useContext,
    useState,
    useCallback,
    useMemo,
    createElement,
} from "react";

import {
    useMutation,
    useQuery,
    useQueryClient,
} from "@tanstack/react-query";

import { authApi } from "../api/authApi";
import { tokenStorage } from "../api/token";
import { authKeys } from "./keys";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [token, setToken] = useState(() => tokenStorage.get());
    const queryClient = useQueryClient();

    const logout = useCallback(() => {
        tokenStorage.clear();
        setToken(null);

        queryClient.cancelQueries({
            queryKey: authKeys.all,
        });

        queryClient.removeQueries({
            queryKey: authKeys.all,
        });
    }, [queryClient]);

    const login = useCallback((accessToken) => {
        tokenStorage.set(accessToken);
        setToken(accessToken);
    }, []);

    const value = useMemo(
        () => ({
            token,
            isAuthenticated: Boolean(token),
            login,
            logout,
        }),
        [token, login, logout]
    );

    return createElement(
        AuthContext.Provider,
        { value },
        children
    );
}

export function useAuth() {
    const context = useContext(AuthContext);

    if (!context) {
        throw new Error("AuthProvider가 필요합니다.");
    }

    return context;
}

export function useMe() {
    const { token, logout } = useAuth();

    return useQuery({
        queryKey: [...authKeys.me, token],
        queryFn: async () => {
            try {
                return await authApi.getMe();
            } catch (error) {
                if (error.response?.status === 401) {
                    logout();
                }
                throw error;
            }
        },
        enabled: Boolean(token),
        retry: false,
        staleTime: 60 * 1000,
    });
}

export function useSignup() {
    return useMutation({
        mutationFn: authApi.signup,
    });
}

export function useVerifyEmail() {
    return useMutation({
        mutationFn: authApi.verifyEmail,
    });
}

export function useResendCode() {
    return useMutation({
        mutationFn: authApi.resendCode,
    });
}

export function useLogin() {
    const { login } = useAuth();
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (credentials) => {
            const data = await authApi.login(credentials);

            if (!data.access_token) {
                throw new Error("로그인 응답에 토큰이 없습니다.");
            }

            return data;
        },
        onSuccess: (data) => {
            queryClient.removeQueries({
                queryKey: authKeys.me,
            });
            login(data.access_token);
        },
    });
}

export function useLogout() {
    const { logout } = useAuth();
    return logout;
}