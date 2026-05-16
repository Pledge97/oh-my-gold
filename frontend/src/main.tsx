import ReactDOM from 'react-dom/client'
import { ConfigProvider, theme } from 'antd'
import App from './App'
import 'antd/dist/reset.css'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#00d4ff',
          colorBgBase: '#060b14',
          colorBgContainer: '#0a1628',
          colorBorder: '#1a3a5c',
          colorText: '#c8d8e8',
          fontFamily: "'Courier New', 'SF Mono', monospace",
          borderRadius: 4,
        },
      }}
    >
      <App />
  </ConfigProvider>
)
