// src/Musicas.js
import React, { useEffect, useState } from 'react';

function Musicas() {
  const [musicas, setMusicas] = useState([]);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    fetch('/api/musicas')
      .then((res) => {
        if (!res.ok) throw new Error('Erro ao buscar músicas');
        return res.json();
      })
      .then((data) => setMusicas(data))
      .catch((err) => setErro(err.message));
  }, []);

  return (
    <div>
      <h2>Músicas disponíveis</h2>
      {erro && <p style={{ color: 'red' }}>{erro}</p>}
      <ul>
        {musicas.map((m, i) => (
          <li key={i}>{m}</li>
        ))}
      </ul>
    </div>
  );
}

export default Musicas;