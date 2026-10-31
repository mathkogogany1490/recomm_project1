import { useState } from "react";
import {
    Modal,
    Form,
    Input,
    Button,
    Alert,
    message,
} from "antd";

import { useSignup } from "../query/useAuth";
import { getApiError } from "../api/client";
import VerifyEmailModal from "./VerifyEmailModal";

export default function SignupModal({ open, onClose }) {
    const [form] = Form.useForm();
    const signupMutation = useSignup();

    const [error, setError] = useState("");
    const [verification, setVerification] = useState(null);

    const handleSignup = async (values) => {
        setError("");

        try {
            const response = await signupMutation.mutateAsync({
                email: values.email,
                password: values.password,
            });

            // 인증 메일 발송 및 서버 시간 정보
            if (
                !response?.expires_at ||
                !response?.resend_available_at ||
                !response?.server_time
            ) {
                throw new Error(
                    "회원가입 응답에 인증 만료 정보가 없습니다."
                );
            }

            setVerification({
                email: values.email,
                response,
            });

            form.resetFields();
            onClose();
        } catch (err) {
            setError(
                err.response
                    ? getApiError(err)
                    : err.message || "회원가입에 실패했습니다."
            );
        }
    };

    const handleVerified = () => {
        setVerification(null);
        message.success("이메일 인증이 완료되었습니다. 로그인해 주세요.");
    };

    const handleClose = () => {
        if (signupMutation.isPending) return;

        setError("");
        form.resetFields();
        onClose();
    };

    return (
        <>
            <Modal
                title="회원가입"
                open={open}
                onCancel={handleClose}
                footer={null}
                destroyOnHidden
                closable={!signupMutation.isPending}
                maskClosable={!signupMutation.isPending}
            >
                {error && (
                    <Alert
                        type="error"
                        title={error}
                        showIcon
                        style={{ marginBottom: 20 }}
                    />
                )}

                <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSignup}
                    autoComplete="off"
                >
                    <Form.Item
                        label="이메일"
                        name="email"
                        rules={[
                            {
                                required: true,
                                message: "이메일을 입력하세요.",
                            },
                            {
                                type: "email",
                                message: "올바른 이메일을 입력하세요.",
                            },
                        ]}
                    >
                        <Input
                            size="large"
                            placeholder="example@gmail.com"
                        />
                    </Form.Item>

                    <Form.Item
                        label="비밀번호"
                        name="password"
                        rules={[
                            {
                                required: true,
                                message: "비밀번호를 입력하세요.",
                            },
                            {
                                min: 8,
                                message: "비밀번호는 8자 이상이어야 합니다.",
                            },
                        ]}
                        hasFeedback
                    >
                        <Input.Password
                            size="large"
                            placeholder="8자 이상 입력"
                        />
                    </Form.Item>

                    <Form.Item
                        label="비밀번호 확인"
                        name="confirmPassword"
                        dependencies={["password"]}
                        hasFeedback
                        rules={[
                            {
                                required: true,
                                message: "비밀번호를 다시 입력하세요.",
                            },
                            ({ getFieldValue }) => ({
                                validator(_, value) {
                                    if (
                                        !value ||
                                        getFieldValue("password") === value
                                    ) {
                                        return Promise.resolve();
                                    }

                                    return Promise.reject(
                                        new Error("비밀번호가 일치하지 않습니다.")
                                    );
                                },
                            }),
                        ]}
                    >
                        <Input.Password
                            size="large"
                            placeholder="비밀번호 확인"
                        />
                    </Form.Item>

                    <Button
                        type="primary"
                        htmlType="submit"
                        size="large"
                        block
                        loading={signupMutation.isPending}
                    >
                        회원가입
                    </Button>
                </Form>
            </Modal>

            <VerifyEmailModal
                open={Boolean(verification)}
                email={verification?.email}
                initialResponse={verification?.response}
                onClose={() => setVerification(null)}
                onVerified={handleVerified}
            />
        </>
    );
}