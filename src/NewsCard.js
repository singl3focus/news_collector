import React from "react";
import "bootstrap/dist/css/bootstrap.min.css";

const NewsCard = ({ title, content, source, date }) => {
  return (
    <div className="container my-3">
      <div className="card shadow-sm border-0 rounded-4">
        <div className="card-body">
          <h5 className="card-title fw-bold text-primary">{title}</h5>
          <p className="card-text text-secondary">{content}</p>

          <div className="d-flex justify-content-between align-items-center mt-4">
            <small className="text-muted">
              <i className="bi bi-globe me-1"></i>Источник: {source}
            </small>
            <small className="text-muted">
              <i className="bi bi-clock me-1"></i>{date}
            </small>
          </div>

          <button className="btn btn-outline-primary btn-sm mt-3">
            Подробнее →
          </button>
        </div>
      </div>
    </div>
  );
};

export default NewsCard;
