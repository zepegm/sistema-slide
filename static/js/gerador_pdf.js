function renderPDF(lista_musicas, lista_categorias, completo, total, loading, btn) {
  const doc = new jspdf.jsPDF({
      orientation: 'portrait',
      unit: 'pt',
      format: 'a5'
  });

  if (completo) {
    var preview = '<div class="conteudo"><div id="capa" class="pagina"><h3 class="titulo"></h3></div>';
    preview += '<div id="info" class="pagina"><div class="titulo"></div></div>';
  } else {
    var preview = '<div class="conteudo">';
  }

  for (item in lista_musicas) {
      preview += '<div id="pag' + lista_musicas[item]['cont'] + '" class="pagina">';
      if (completo) {
          preview += '<h3 class="titulo">' + lista_musicas[item]['cont'] + '. ' + lista_musicas[item]['titulo'] + '</h3>';
      } else {
          preview += '<h3 class="titulo">' + lista_musicas[item]['titulo'] + '</h3>';
      }

      preview += '<div class="content">';
          for (musica in lista_musicas[item]['letras']) {
              preview += "<p class='paragrafo'>" + lista_musicas[item]['letras'][musica]['texto'] + "</p>";
          }

      preview += '</div></div>';
  }

  preview += "</div>";

  //console.log(preview);

  doc.html(preview, {
  //doc.html(document.body, {
      html2canvas: {
          scale: 1,
      },
      callback: (pdf) => {
          if (completo) {
              // adicionar capa
              doc.setPage(1);
              const date = new Date().toLocaleDateString("pt-BR");

              doc.setLineWidth(4);
              doc.line(20, 20, 400, 20);
              doc.line(20, 575, 400, 575);
          
              doc.line(20, 18, 20, 577);
              doc.line(400, 18, 400, 577);
          
              doc.setLineWidth(0.01);
              doc.line(25, 25, 395, 25);
              doc.line(25, 570, 395, 570);
          
              doc.line(25, 25, 25, 570);
              doc.line(395, 25, 395, 570);
                              
          
              doc.setFont('BebasKai', 'normal');
              doc.setFontSize(33);
              doc.text(210, 56, 'Assembleia de Deus Ministério', 'center');
              doc.text(210, 96, 'De Cachoeira Paulista', 'center');
          
              var img = new Image();
          
              img.src = "/static/images/Logo%20Colorido.png";
              doc.addImage(img, 'png', 141, 170, 141, 170, undefined, 'FAST');
          
              doc.setTextColor(255, 0, 0);
              doc.setFontSize(50);
              doc.text(210, 453, 'Hinário dos Slides', 'center');
          
              doc.setTextColor(0, 0, 0);
              doc.setFont('helvetica', 'normal'); 
              doc.setFontSize(20);
              doc.text(210, 552, date, 'center')      

              // adicionar informações
              doc.setPage(2);
              doc.setFontSize(20);
              doc.setTextColor(0, 0, 0);
              doc.setFont('BebasKai', 'normal');
              doc.text(209, 48, 'Informações do documento', 'center');
              tamanho = doc.getTextWidth('Informações do documento');

              doc.setLineWidth(0.08);
              doc.line(209 - (tamanho / 2), 54, 209 + (tamanho / 2), 54);

              doc.setFont('helvetica', 'normal'); 
              doc.setFontSize(12);
              y = 85;
              doc.text(20, y, 'Documento gerado automaticamente pelo banco de dados do sistema');
              doc.setFont('helvetica', 'bold'); 
              y += 20;
              doc.text(20, y, '"Slide Master Index II".');

              y += 40;
              doc.text(20, y, 'Data do documento: ');
              tamanho = doc.getTextWidth('Data do documento: ');
              doc.setFont('helvetica', 'normal'); 
              doc.text(20 + tamanho, y, date);

              y += 20;
              doc.setFont('helvetica', 'bold'); 
              doc.text(20, y, 'Quantidade de Músicas: ');
              tamanho = doc.getTextWidth('Quantidade de Músicas: ');
              doc.setFont('helvetica', 'normal'); 
              doc.text(20 + tamanho, y, String(total));

              y += 40;
              doc.setFont('helvetica', 'bold'); 
              doc.text(20, y, 'Vínculos: ');
              x = 20;
              y += 20;
              doc.setFont('helvetica', 'normal');

              // agora que a dificuldade começa rs
              for (item in lista_categorias) {
                  doc.setFontSize(12);
                  doc.text(x, y, lista_categorias[item]['descricao']);
                  y += 14;
                  doc.setFontSize(10);
                  for (sub in lista_categorias[item]['cats']) {
                      doc.text(x, y, " - " + lista_categorias[item]['cats'][sub])
                      y += 14;
                  }

                  y += 14;
              }                        
          }

          var pageCount = doc.internal.getNumberOfPages();
          doc.deletePage(pageCount)

          doc.setProperties({
              title: "Lista de Músicas"
          });


          window.open(doc.output('bloburl'), '_blank');  

          loading.attr('hidden', '');
          btn.removeAttr('disabled');

          /*if (completo) {
              doc.save('musicas.pdf', { returnPromise: true }).then(() => {
                  console.log('yes');
                  //window.close();
              });                        
          } else {
              window.open(doc.output('bloburl'), '_blank');  
              window.close();
          }*/

      },
      /*x: 10,
      y: 10*/
  });


}

function addPaginaInferior(doc, pagina) {
    doc.setFont('helvetica', 'normal'); 
    doc.setFontSize(11);
    doc.setTextColor(0, 0, 0);
    doc.text(7.4, 20.5, pagina, 'center');
  }

  function gerarPDF(lista, lista_categorias, extras) {

    var doc = new jsPDF({
        orientation: 'portrait',
        unit: 'cm',
        format: 'a5'
    });

    const date = new Date().toLocaleDateString("pt-BR");
    pagina = 1;

    console.log(extras);

    // capa
    if (extras) {
      doc.setLineWidth(0.15);
      doc.line(0.7, 0.7, 14.1, 0.7);
      doc.line(0.7, 20.3, 14.1, 20.3);
  
      doc.line(0.7, 0.625, 0.7, 20.375);
      doc.line(14.1, 0.625, 14.1, 20.375);
  
      doc.setLineWidth(0.01);
      doc.line(0.9, 0.9, 13.9, 0.9);
      doc.line(0.9, 20.1, 13.9, 20.1);
  
      doc.line(0.9, 0.9, 0.9, 20.1);
      doc.line(13.9, 0.9, 13.9, 20.1);
  
  
      doc.setFont('BebasKai', 'normal');
      doc.setFontSize(33);
      doc.text(7.4, 2, 'Assembleia de Deus Ministério', 'center');
      doc.text(7.4, 3.4, 'De Cachoeira Paulista', 'center');
  
      var img = new Image();
  
      img.src = "/static/images/Logo%20Colorido.png";
      doc.addImage(img, 'png', 5, 6, 5, 6, undefined, 'FAST');
  
      doc.setTextColor(255, 0, 0);
      doc.setFontSize(50);
      doc.text(7.4, 16, 'Hinário dos Slides', 'center');
  
      doc.setTextColor(0, 0, 0);
      doc.setFont('helvetica', 'normal'); 
      doc.setFontSize(20);
      doc.text(7.4, 19.5, date, 'center')
  
  
      doc.addPage();
      pagina++;
    }

    // Informações do documento
    if (extras) {
      doc.setFontSize(20);
      doc.setTextColor(0, 0, 0);
      doc.setFont('BebasKai', 'normal');
      doc.text(7.4, 1.7, 'Informações do documento', 'center');
      tamanho = doc.getTextWidth('Informações do documento');

      doc.setLineWidth(0.08);
      doc.line(7.4 - (tamanho / 2), 1.9, 7.4 + (tamanho / 2), 1.9);

      doc.setFont('helvetica', 'normal'); 
      doc.setFontSize(12);
      y = 3;
      doc.text(0.7, y, 'Documento gerado automaticamente pelo banco de dados do sistema');
      doc.setFont('helvetica', 'bold'); 
      y += 0.7;
      doc.text(0.7, y, '"Slide Master Index II".');

      y += 1.4;
      doc.text(0.7, y, 'Data do documento: ');
      tamanho = doc.getTextWidth('Data do documento: ');
      doc.setFont('helvetica', 'normal'); 
      doc.text(0.7 + tamanho, y, date);

      y += 0.7;
      doc.setFont('helvetica', 'bold'); 
      doc.text(0.7, y, 'Quantidade de Músicas: ');
      tamanho = doc.getTextWidth('Quantidade de Músicas: ');
      doc.setFont('helvetica', 'normal'); 
      doc.text(0.7 + tamanho, y, String(lista.length));

      y += 1.4;
      doc.setFont('helvetica', 'bold'); 
      doc.text(0.7, y, 'Vínculos: ');
      x = 0.7;
      y += 0.7;
      doc.setFont('helvetica', 'normal');

      // agora que a dificuldade começa rs
      for (item in lista_categorias) {
        doc.setFontSize(12);
        doc.text(x, y, lista_categorias[item]['descricao']);
        y += 0.5;
        doc.setFontSize(10);
        for (sub in lista_categorias[item]['subcategoria']) {
          doc.text(x, y, " - " + lista_categorias[item]['subcategoria'][sub]['descricao'])
          y += 0.5;
        }

        y += 0.5;
      }


      // Esqueleto básico do Sumário:
      doc.addPage();
      pagina++;
      doc.setFontSize(20);
      doc.setTextColor(0, 0, 0);
      doc.setFont('BebasKai', 'normal');
      doc.text(7.4, 1.2, 'Sumário', 'center');
      tamanho = doc.getTextWidth('Sumário');

      doc.setLineWidth(0.08);
      doc.line(7.4 - (tamanho / 2), 1.4, 7.4 + (tamanho / 2), 1.4);    

      doc.addPage();
      pagina++;     
      
      // preciso calcular as páginas extras
      if (lista.length > 30) {
        sobra = lista.length - 30;
        total_pags = Math.ceil((sobra / 32));
        
        for (let i = 0; i < total_pags; i++) {
          doc.addPage();
          pagina++;    
        }         
      }
    }

    // página das músicas
    var cont = 1;
    doc.setLineWidth(0.01);

    for (musica in lista) {
      lista[musica]['pagina'] = pagina;

      // inicialização das posições
      x = 1.27;
      y = 1.27;

      // escrever título
      doc.setFont('BebasKai', 'normal');
      doc.setFontSize(20);
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


            doc.text(x, aux, lista[musica]['letras'][paragrafo][linha]['text'][texto]);

            if (aux_css == 'ignore') {
              tamanho = doc.getTextWidth(lista[musica]['letras'][paragrafo][linha]['text'][texto]);
            } else {
              tamanho = doc.getTextWidth(lista[musica]['letras'][paragrafo][linha]['text'][texto] + ' ');
            }

            if (aux_css == 'u' || aux_css == 'mark-u' || aux_css == 'u-b') {
              doc.line(x, y + 0.1, doc.getTextWidth(lista[musica]['letras'][paragrafo][linha]['text'][texto]) + x, y + 0.1);
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

    // refazer sumário
    if (extras) {
      pag_sum = 3;
      doc.setPage(pag_sum);
    
      x = 0.7;
      y = 2.4;
  
      doc.setFontSize(9);
      doc.setFont('helvetica', 'normal');
  
      cont = 1;
      doc.setLineWidth(0.01);
      doc.setLineDash([0.05, 0.05], 0);
      limite = 31;
  
      for (musica in lista) {
        doc.text(x, y, cont.toString().padStart(2, '0') + '. ' + lista[musica]['titulo']);
        doc.line(x + doc.getTextWidth(cont.toString().padStart(2, '0') + '. ' + lista[musica]['titulo'] + ' '), y, 14.1 - doc.getTextWidth(String(lista[musica]['pagina'])) - doc.getTextWidth(' '), y);
        doc.text(14.1 ,y, String(lista[musica]['pagina']), 'right');
  
        // desenhar retângulo do link
        /*doc.setDrawColor(255, 0, 0);
        doc.rect(x, y - 0.3, 13.4, 0.4, 'S');*/
        doc.link(x, y - 0.3, 13.4, 0.4, { pageNumber: lista[musica]['pagina'], magFactor: 'XYZ' });
        //doc.setDrawColor(0, 0, 0);
  
        y += 0.6;
        cont++;

        if (cont == limite) {
          pag_sum++;
          doc.setPage(pag_sum)
          y = 1.2;
          doc.setLineWidth(0.01);
          doc.setLineDash([0.05, 0.05], 0);          
          limite += 32;
        }
      }
    }
    
    window.open(doc.output('bloburl'), '_blank');   

  }