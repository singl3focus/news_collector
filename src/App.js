import logo from './logo.svg';
import './App.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  LineElement,
  BarElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { useEffect, useRef, useState } from 'react';

ChartJS.register(
  LineElement,
  BarElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Title,
  Tooltip,
  Legend
);

const data = {
  labels: ['Янв', 'Фев', 'Мар', 'Апр'],
  datasets: [
    {
      label: 'Продажи',
      data: [150, 200, 180, 220],
      backgroundColor: 'rgba(54, 162, 235, 0.5)',
      borderColor: 'rgba(54, 162, 235, 1)',
      tension: 0.3
    },
  ],
};


function App() {
  const [news, setNews] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    wsRef.current = new WebSocket('ws://192.168.52.12:9999');

    wsRef.current.onmessage = (event) => {
      const message = event.data;

      setNews((prev) => [
        { id: Date.now(), text: message },
        ...prev.slice(0, 19), // храним только 20 последних новостей
      ]);
    };

    wsRef.current.onerror = (err) => {
      console.error('WebSocket error:', err);
    };

    wsRef.current.onclose = () => {
      console.log('WebSocket closed');
    };

    // Очистка при размонтировании
    return () => {
      wsRef.current?.close();
    };
  },[])

  return (
    <div className="App">
      <div className='news_wrapper border-primary shadow-sm'>
        <h1 class="display-5">Последние новости</h1>
        {
          news.map((item, index) => {
            return (
              <NewsCard
                title={item.text}
                content="Мир — это не данная истина. Это чья-то конструкция. Все формы, привычки, ограничения и правила — лишь след от чужих решений."
                source="https://t.me/somechannel"
                date="7 июня 2025"
                isHighlited={index==0}
              />
            )
          })
        }
      </div>
      <div className='dashboard_wrapper'>
         <h1 class="display-5">Дашборд</h1>
         <Line data={data} />
      </div>
    </div>
  );
}

const NewsCard = ({ title, summary, source, time, isHighlited}) => {
  return (
    <div className="container my-1">
      <div className={`card ${isHighlited ? "border-primary" : "border"} rounded shadow-sm p-3`}>
        <div className="card-body">
          <h5 className="card-title fw-bold">{title}</h5>
          <p className="card-text text-muted">{summary}</p>
          <div className="d-flex justify-content-between mt-3">
            <span className="badge bg-primary">{source}</span>
            <small className="text-secondary">{time}</small>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
