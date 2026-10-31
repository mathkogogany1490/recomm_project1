import { useState } from "react";
import { Modal, Form, Input, Button, Alert } from "antd";

import { useLogin } from "../query/useAuth";
import { getApiError } from "../api/client";

export default function LoginModal({ open, onClose }) {
    const [form] = Form.useForm();
    const [error, setError] = useState("");

    const loginMutation = useLogin();

    const handleLogin = async (values) => {
        setError("");

        try {
            await loginMutation.mutateAsync(values);
            form.resetFields();
            onClose();
        } catch (err) {
            setError(getApiError(err));
        }
    };

    const handleClose = () => {
        if (loginMutation.isPending) return;

        form.resetFields();
        setError("");
        onClose();
    };

    return (
        <Modal
            title="로그인"
            open={open}
            onCancel={handleClose}
            footer={null}
            destroyOnHidden
            maskClosable={!loginMutation.isPending}
            closable={!loginMutation.isPending}
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
                onFinish={handleLogin}
                autoComplete="off"
            >
                <Form.Item
                    label="이메일"
                    name="email"
                    rules={[
                        { required: true, message: "이메일을 입력하세요." },
                        { type: "email", message: "이메일 형식이 아닙니다." },
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
                        { required: true, message: "비밀번호를 입력하세요." },
                    ]}
                >
                    <Input.Password
                        size="large"
                        placeholder="비밀번호"
                    />
                </Form.Item>

                <Button
                    type="primary"
                    htmlType="submit"
                    size="large"
                    block
                    loading={loginMutation.isPending}
                >
                    로그인
                </Button>
            </Form>
        </Modal>
    );
}