import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Container,
  Tabs,
  Tab,
  CircularProgress
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  
  // ログインフォーム
  const [loginData, setLoginData] = useState({
    username: '',
    password: ''
  });
  
  // 登録フォーム
  const [registerData, setRegisterData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    full_name: ''
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    setError('');
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await axios.post(
        `${process.env.REACT_APP_API_URL}/auth/login`,
        new URLSearchParams({
          username: loginData.username,
          password: loginData.password
        }),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        }
      );

      if (response.data.access_token) {
        login(response.data.access_token, response.data.refresh_token);
        navigate('/');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'ログインに失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    // パスワード確認
    if (registerData.password !== registerData.confirmPassword) {
      setError('パスワードが一致しません');
      return;
    }
    
    setLoading(true);

    try {
      // 登録
      await axios.post(
        `${process.env.REACT_APP_API_URL}/auth/register`,
        {
          email: registerData.email,
          username: registerData.username,
          password: registerData.password,
          full_name: registerData.full_name
        }
      );

      // 登録成功後、自動ログイン
      const loginResponse = await axios.post(
        `${process.env.REACT_APP_API_URL}/auth/login`,
        new URLSearchParams({
          username: registerData.username,
          password: registerData.password
        }),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        }
      );

      if (loginResponse.data.access_token) {
        login(loginResponse.data.access_token, loginResponse.data.refresh_token);
        navigate('/');
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '登録に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  const handleSkip = () => {
    // ゲストとして続行
    navigate('/');
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 8, mb: 4 }}>
        <Typography variant="h4" align="center" gutterBottom>
          動画会計アプリ
        </Typography>
        <Card>
          <CardContent>
            <Tabs value={tabValue} onChange={handleTabChange} centered>
              <Tab label="ログイン" />
              <Tab label="新規登録" />
            </Tabs>

            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}

            <TabPanel value={tabValue} index={0}>
              <form onSubmit={handleLogin}>
                <TextField
                  fullWidth
                  label="ユーザー名またはメール"
                  variant="outlined"
                  margin="normal"
                  value={loginData.username}
                  onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                  required
                  disabled={loading}
                />
                <TextField
                  fullWidth
                  label="パスワード"
                  type="password"
                  variant="outlined"
                  margin="normal"
                  value={loginData.password}
                  onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                  required
                  disabled={loading}
                />
                <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    disabled={loading}
                  >
                    {loading ? <CircularProgress size={24} /> : 'ログイン'}
                  </Button>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={handleSkip}
                    disabled={loading}
                  >
                    ゲストとして続行
                  </Button>
                </Box>
              </form>
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              <form onSubmit={handleRegister}>
                <TextField
                  fullWidth
                  label="メールアドレス"
                  type="email"
                  variant="outlined"
                  margin="normal"
                  value={registerData.email}
                  onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                  required
                  disabled={loading}
                />
                <TextField
                  fullWidth
                  label="ユーザー名"
                  variant="outlined"
                  margin="normal"
                  value={registerData.username}
                  onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })}
                  required
                  disabled={loading}
                />
                <TextField
                  fullWidth
                  label="氏名（オプション）"
                  variant="outlined"
                  margin="normal"
                  value={registerData.full_name}
                  onChange={(e) => setRegisterData({ ...registerData, full_name: e.target.value })}
                  disabled={loading}
                />
                <TextField
                  fullWidth
                  label="パスワード"
                  type="password"
                  variant="outlined"
                  margin="normal"
                  value={registerData.password}
                  onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                  required
                  disabled={loading}
                />
                <TextField
                  fullWidth
                  label="パスワード（確認）"
                  type="password"
                  variant="outlined"
                  margin="normal"
                  value={registerData.confirmPassword}
                  onChange={(e) => setRegisterData({ ...registerData, confirmPassword: e.target.value })}
                  required
                  disabled={loading}
                />
                <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    disabled={loading}
                  >
                    {loading ? <CircularProgress size={24} /> : '登録'}
                  </Button>
                  <Button
                    fullWidth
                    variant="outlined"
                    onClick={handleSkip}
                    disabled={loading}
                  >
                    ゲストとして続行
                  </Button>
                </Box>
              </form>
            </TabPanel>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
};

export default Login;