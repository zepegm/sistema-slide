import React from 'react';
import SlideShow from './components/SlideShow';
import slideData from './data/slides.json'; // ou use fetch se preferir

const App = () => {
  return (
    <SlideShow
      slides={slideData}
      config={{ letra: '#fff', fundo: '#000', mark: '#ffcc00' }}
      fundo="images/fundo_padrao.jpg"
      socketUrl="http://localhost:5000"
    />
  );
};

export default App;