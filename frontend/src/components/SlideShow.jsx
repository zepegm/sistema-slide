// frontend/src/components/SlideShow.jsx
import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import textFit from 'textfit';
import './SlideShow.css'; // Assuma que aqui estão os estilos copiados do Flask

const SlideShow = ({ slides = [], config, fundo, socketUrl }) => {
  const [indexAtual, setIndexAtual] = useState(0);
  const [chave, setChave] = useState(0); // alterna entre 0 e 1
  const [finalizado, setFinalizado] = useState(false);
  const slideRefs = [useRef(null), useRef(null)];
  const notasRef = useRef(null);

  useEffect(() => {
    const socket = io(socketUrl);

    socket.on('update', (index) => {
      if (finalizado) {
        window.location.reload();
        return;
      }
      setIndexAtual(index);
      setChave((prev) => 1 - prev); // alterna entre 0 e 1
    });

    socket.on('refresh', () => window.location.reload());
    socket.on('pix', () => window.location.replace('/slide_pix'));
    socket.on('wait_pptx', () => window.location.replace('/wait_pptx'));
    socket.on('change_wallpaper', () => {
      if (slides.length === 0) window.location.reload();
    });

    return () => socket.disconnect();
  }, [finalizado, slides.length, socketUrl]);

  useEffect(() => {
    const atual = slideRefs[chave].current;
    const anterior = slideRefs[1 - chave].current;
    if (!atual || !anterior) return;

    anterior.className = 'slide out';
    atual.className = 'slide in';

    if (indexAtual === 0 || indexAtual - 1 === slides.length) {
      atual.innerHTML = '';
      atual.classList.add('capa');
      if (indexAtual - 1 === slides.length) {
        atual.classList.add('final-out');
        setFinalizado(true);
        // animar texto "Fim..." com Vara.js se quiser depois
      }
    } else {
      const slide = slides[indexAtual - 1];
      atual.classList.remove('capa');
      atual.classList.add('letra');
      atual.innerHTML = slide['text-slide'];

      if ([3, 4].includes(slide.categoria)) {
        notasRef.current.innerHTML = `<div class="noot-1">♫ ♩</div><div class="noot-2">♩</div><div class="noot-3">♯ ♪</div><div class="noot-4">♪</div>`;
      } else {
        notasRef.current.innerHTML = '';
      }

      if ([2, 4].includes(slide.categoria)) {
        atual.classList.add('coro');
      }

      textFit(atual, { alignVert: true, multiLine: true, minFontSize: 20, maxFontSize: 1000 });
    }
  }, [indexAtual, chave, slides]);

  return (
    <div>
      <div ref={notasRef} className="muzieknootjes"></div>
      <div ref={slideRefs[0]} id="slide1" className="slide" />
      <div ref={slideRefs[1]} id="slide2" className="slide" />
      <div id="fim"></div>
    </div>
  );
};

export default SlideShow;
