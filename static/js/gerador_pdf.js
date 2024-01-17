function addPaginaInferior(doc, pagina) {
    doc.setFont('helvetica', 'normal'); 
    doc.setFontSize(11);
    doc.setTextColor(0, 0, 0);
    doc.text(7.4, 20.5, pagina, 'center');
  }

  function gerarPDF(lista) {

    var doc = new jsPDF({
        orientation: 'portrait',
        unit: 'cm',
        format: 'a5'
    });

    doc.addPage();

    var cont = 1;
    doc.setLineWidth(0.01);

    pagina = 1;

    for (musica in lista) {
      // inicialização das posições
      x = 1.27;
      y = 1.27;

      // escrever título
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(13);
      doc.setTextColor(0, 112, 192);
      doc.text(7.4, y, ("0" + cont).slice(-2) + ". " + lista[musica]['titulo'], 'center');

      y += 1;

      doc.setFont('helvetica', 'normal'); 
      doc.setTextColor(0, 0, 0);
      doc.setFontSize(10);

      for (paragrafo in lista[musica]['letras']) {

        aux_css = '0';

        for (linha in lista[musica]['letras'][paragrafo]) {

          if (aux_css == lista[musica]['letras'][paragrafo][linha]['css'] || lista[musica]['letras'][paragrafo][linha]['css'] == "br") {
            x = 1.27;

                
            if (lista[musica]['letras'][paragrafo][linha]['css'] == 'br') {
              if (parseInt(linha) + 1 < lista[musica]['letras'][paragrafo].length) {
                y += 0.5;

                if (y > 19.5) {
                  addPaginaInferior(doc, ("0" + pagina).slice(-2));
                  pagina++;
                  doc.addPage();
                  y = 1.27;
                }                  
              }
            } else {
              y += 0.5;

              if (y > 19.5 && parseInt(linha) + 1 < lista[musica]['letras'][paragrafo].length) {
                addPaginaInferior(doc, ("0" + pagina).slice(-2));
                pagina++;                  
                doc.addPage();
                y = 1.27;
              }                
            }

          }

          aux_css = lista[musica]['letras'][paragrafo][linha]['css'];

          if (aux_css == 'mark') {
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(192, 0, 0);
          } else if (aux_css == 'b' || aux_css == "u-b") {
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(0, 0, 0);
            doc.setDrawColor(0, 0, 0);
          } else if (aux_css == 'mark-u') {
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(192, 0, 0);
            doc.setDrawColor(192, 0, 0);
          } else if (aux_css == 'i') {
            doc.setFont('helvetica', 'italic');
            doc.setTextColor(0, 0, 0);
            doc.setDrawColor(0, 0, 0);              
          } else {
            doc.setFont('helvetica', 'normal');
            doc.setTextColor(0, 0, 0);  
            doc.setDrawColor(0, 0, 0);     
          }

          aux = y;

          for (texto in lista[musica]['letras'][paragrafo][linha]['text']) {

            if (aux != y) {
              y = aux;
              x = 1.27;

              if (y > 19.5 && parseInt(texto) + 1 < lista[musica]['letras'][paragrafo][linha]['text'].length) {
                addPaginaInferior(doc, ("0" + pagina).slice(-2));
                pagina++;                  
                doc.addPage();
                y = 1.27;
              }                
            }

            doc.text(x, aux, lista[musica]['letras'][paragrafo][linha]['text'][texto] + ' ');
            tamanho = doc.getTextWidth(lista[musica]['letras'][paragrafo][linha]['text'][texto] + ' ');

            if (aux_css == 'u' || aux_css == 'mark-u' || aux_css == 'u-b') {
              doc.line(x, y + 0.07, doc.getTextWidth(lista[musica]['letras'][paragrafo][linha]['text'][texto]) + x, y + 0.07);
            }

            x += tamanho;

            aux += 0.5;
          }

        }
        
        x = 1.27;
        y += 0.7;

        if (y > 19.5 && parseInt(paragrafo) + 1 < lista[musica]['letras'][paragrafo].length) {
          addPaginaInferior(doc, ("0" + pagina).slice(-2));
          pagina++;            
          doc.addPage();
          y = 1.27;
        }
      }

      if (parseInt(musica) + 1 < lista.length) {
        addPaginaInferior(doc, ("0" + pagina).slice(-2));
        pagina++;          
        doc.addPage();
        cont++;
      }
      
    }

    addPaginaInferior(doc, ("0" + pagina).slice(-2));
    /*doc.setPage(1);
    doc.text(10, 10, 'yes');*/
    window.open(doc.output('bloburl'), '_blank');   

  }