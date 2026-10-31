import { useEffect, useMemo, useState } from "react";
import {
    Modal,
    Form,
    Input,
    Button,
    Alert,
    Typography,
    Space,
} from "antd";

import {
    useVerifyEmail,
    useResendCode,
} from "../query/useAuth";

import { getApiError } from "../api/client";

const { Text, Title } = Typography;

function getTimeState(response) {
    if (
        !response?.expires_at ||
        !response?.resend_available_at ||
        !response?.server_time
    ) {
        throw new Error(
            "서버에서 인증번호 만료 시간을 받지 못했습니다."
        );
    }

    const expiresAt = Date.parse(response.expires_at);
    const resendAt = Date.parse(response.resend_available_at);
    const serverTime = Date.parse(response.server_time);

    if (
        !Number.isFinite(expiresAt) ||
        !Number.isFinite(resendAt) ||
        !Number.isFinite(serverTime)
    ) {
        throw new Error("서버 시간 형식이 올바르지 않습니다.");
    }

    return {
        expiresAt,
        resendAt,
        serverTime,
        receivedAt: Date.now(),
    };
}

function formatSeconds(seconds) {
    const minutes = String(Math.floor(seconds / 60))
        .padStart(2, "0");

    const remain = String(seconds % 60).padStart(2, "0");

    return `${minutes}:${remain}`;
}

export default function VerifyEmailModal({
                                             open,
                                             email,
                                             initialResponse,
                                             onClose,
                                             onVerified,
                                         }) {
    const [form] = Form.useForm();
    const [error, setError] = useState("");
    const [now, setNow] = useState(Date.now());
    const [timeState, setTimeState] = useState(null);

    const verifyMutation = useVerifyEmail();
    const resendMutation = useResendCode();

    useEffect(() => {
        if (!open) return;

        form.resetFields();
        setError("");

        try {
            setTimeState(getTimeState(initialResponse));
        } catch (err) {
            setTimeState(null);
            setError(err.message);
        }
    }, [open, initialResponse, form]);

    useEffect(() => {
        if (!open) return;

        const interval = setInterval(() => {
            setNow(Date.now());
        }, 1000);

        return () => clearInterval(interval);
    }, [open]);

    const serverNow = useMemo(() => {
        if (!timeState) return null;

        return (
            timeState.serverTime +
            (now - timeState.receivedAt)
        );
    }, [timeState, now]);

    const remainingSeconds = timeState
        ? Math.max(
            0,
            Math.ceil((timeState.expiresAt - serverNow) / 1000)
        )
        : 0;

    const resendSeconds = timeState
        ? Math.max(
            0,
            Math.ceil((timeState.resendAt - serverNow) / 1000)
        )
        : 0;

    const expired = remainingSeconds <= 0;
    const canResend = resendSeconds <= 0;

    const handleVerify = async ({ code }) => {
        if (expired) {
            setError("인증번호가 만료되었습니다. 다시 보내 주세요.");
            return;
        }

        setError("");

        try {
            await verifyMutation.mutateAsync({
                email,
                code,
            });

            form.resetFields();
            onVerified();
        } catch (err) {
            setError(getApiError(err));
        }
    };

    const handleResend = async () => {
        if (!canResend || resendMutation.isPending) return;

        setError("");

        try {
            const response = await resendMutation.mutateAsync(email);

            setTimeState(getTimeState(response));
            setNow(Date.now());
            form.resetFields();
        } catch (err) {
            setError(getApiError(err));
        }
    };

    const pending =
        verifyMutation.isPending || resendMutation.isPending;

    return (
        <Modal
            title="이메일 인증"
            open={open}
            onCancel={onClose}
            footer={null}
            destroyOnHidden
            closable={!pending}
            maskClosable={false}
            keyboard={!pending}
        >
            <Text>
                <strong>{email}</strong> 주소로 발송된
                인증번호 6자리를 입력하세요.
            </Text>

            {error && (
                <Alert
                    type="error"
                    title={error}
                    showIcon
                    style={{ marginTop: 20 }}
                />
            )}

            <div style={{ textAlign: "center", margin: "28px 0" }}>
                <Title
                    level={2}
                    style={{
                        margin: 0,
                        color: expired ? "#ff4d4f" : "#1677ff",
                    }}
                >
                    {formatSeconds(remainingSeconds)}
                </Title>

                <Text type="secondary">
                    {expired
                        ? "인증번호가 만료되었습니다."
                        : "인증번호 유효 시간"}
                </Text>
            </div>

            <Form
                form={form}
                layout="vertical"
                onFinish={handleVerify}
            >
                <Form.Item
                    name="code"
                    rules={[
                        {
                            required: true,
                            message: "인증번호를 입력하세요.",
                        },
                        {
                            pattern: /^\d{6}$/,
                            message: "숫자 6자리를 입력하세요.",
                        },
                    ]}
                >
                    <Input.OTP
                        length={6}
                        size="large"
                        disabled={expired || pending}
                        style={{ justifyContent: "center" }}
                    />
                </Form.Item>

                <Button
                    type="primary"
                    htmlType="submit"
                    block
                    size="large"
                    disabled={expired || !timeState}
                    loading={verifyMutation.isPending}
                >
                    인증 확인
                </Button>
            </Form>

            <div style={{ textAlign: "center", marginTop: 20 }}>
                <Space direction="vertical">
                    <Text type="secondary">
                        인증번호를 받지 못하셨나요?
                    </Text>

                    <Button
                        type="link"
                        onClick={handleResend}
                        disabled={!canResend || pending}
                        loading={resendMutation.isPending}
                    >
                        {canResend
                            ? "인증번호 다시 보내기"
                            : `다시 보내기 (${formatSeconds(resendSeconds)})`}
                    </Button>
                </Space>
            </div>
        </Modal>
    );
}