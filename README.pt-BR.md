# SimilarImageFinder

[![Python](https://github.com/CaiqueDourado/SimilarImageFinder/actions/workflows/python.yml/badge.svg)](https://github.com/CaiqueDourado/SimilarImageFinder/actions/workflows/python.yml)
[![.NET](https://github.com/CaiqueDourado/SimilarImageFinder/actions/workflows/dotnet.yml/badge.svg)](https://github.com/CaiqueDourado/SimilarImageFinder/actions/workflows/dotnet.yml)
[![Licença: MIT](https://img.shields.io/badge/licença-MIT-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![.NET 8](https://img.shields.io/badge/.NET-8.0-512BD4)

[Read in English](README.md)

**Encontra imagens duplicadas e quase duplicadas, em especial fotos de produto.** Hashes perceptuais (aHash, dHash, pHash), remoção de borda, um índice de busca exata para milhões de hashes e um detector de imagens genéricas. Um algoritmo, duas implementações: **Python e .NET devolvem os mesmos bits** para os mesmos pixels, conferido por vetores de teste compartilhados.

```python
from similar_image_finder import perceptual_hash

a = perceptual_hash("loja-a/luminaria.jpg")
b = perceptual_hash("loja-b/pendente-preto-600x600.webp")
a - b          # distância de Hamming: 0-6 = mesma foto, 20+ = diferentes
```

```csharp
using SimilarImageFinder;

var a = ImageLoader.Hash("loja-a/luminaria.jpg");                 // pHash, 64 bits
var b = ImageLoader.Hash("loja-b/pendente-preto-600x600.webp");
var distancia = a - b;
```

```bash
similar-image-finder dupes ./fotos -r --max-distance 6 --trim > grupos.csv
```

## De onde veio

Entre 2019 e 2024 eu mantive um catálogo de **114,6 milhões de ofertas de 7.179 lojas brasileiras** ([catalogo-produtos-ecommerce-brasil](https://github.com/CaiqueDourado/catalogo-produtos-ecommerce-brasil)). Cada foto de produto foi baixada (85,8 milhões de tarefas de download em 12 a 15 máquinas), reduzida a 16×16 em cinza e passada por SHA-256. A assinatura era uma das chaves que ligavam o mesmo produto em lojas diferentes, e uma imagem presente em mais de 100 produtos era marcada como genérica.

Ela funcionava para o que conseguia ver: lojas do mesmo grupo servindo o mesmo arquivo e imagens "sem foto". Duas coisas que ela não fazia viraram esta biblioteca:

1. **Só reconhecia arquivos idênticos.** O SHA-256 muda por inteiro quando um pixel muda em 1, então uma foto que a loja redimensionou ou recomprimiu ganhava outra assinatura.

   <p align="center"><img src="docs/img/exact-vs-perceptual-hash.pt-BR.png" alt="A mesma foto com 1000 e 300 pixels: SHA-256 diferentes, dHash a 1 bit de distância" width="860"></p>

2. **A assinatura dependia da máquina.** Quando as imagens foram para a AWS e o hash foi calculado de novo, os valores não bateram com os locais. O código antigo passava pelo hash o *arquivo codificado* da miniatura 16×16, cujos bytes podem mudar com a versão do codificador; é a causa mais provável. Aqui todo hash sai dos pixels decodificados, com aritmética inteira, e é o mesmo em qualquer máquina e nas duas linguagens.

## Qual hash usar

Medi cada método em 300 fotos sintéticas de produto, cada uma com 11 edições que as lojas fazem (redimensionar, recomprimir, recortar, pôr borda, marca d'água…), e em todos os 44.850 pares de produtos *diferentes*. Os produtos são difíceis de separar de propósito: fundo branco e os mesmos seis tipos de objeto. O teste está em [`evaluation/`](evaluation/) e roda em cerca de um minuto.

<p align="center"><img src="docs/img/false-matches.pt-BR.png" alt="Pares de produtos diferentes casados por distância: aHash e dHash sobem rápido, pHash fica perto de zero" width="760"></p>

**aHash e dHash confundem fotos de produtos diferentes.** Com fundo branco, a maior parte dos bits descreve o fundo. Com até 6 bits de distância, 7,7% (aHash) e 1,9% (dHash) dos pares de produtos *diferentes* parecem duplicados, e alguns produtos diferentes ficam com o hash idêntico. O pHash fica em 0,22%.

Cópias editadas encontradas com até 6 bits de distância (hashes de 64 bits):

| Edição | SHA-256 exato | aHash | dHash | pHash | pHash + trim |
|---|---:|---:|---:|---:|---:|
| reduzir a 50% | 3% | 100% | 100% | 100% | 100% |
| reduzir a 25% | 0% | 100% | 99% | 100% | 99% |
| JPEG qualidade 30 | 0% | 100% | 100% | 100% | 99% |
| reduzir a 50% + JPEG 60 | 0% | 100% | 100% | 100% | 86% |
| redimensionar sem manter a proporção | 11% | 100% | 100% | 100% | 100% |
| brilho +15% | 0% | 100% | 100% | 99% | 98% |
| recortar 5% de cada lado | 0% | 93% | 55% | 11% | **96%** |
| borda branca de 10% | 0% | 60% | 9% | 5% | **78%** |
| marca d'água no canto | 0% | 95% | 100% | 35% | 0% |
| girar 3° | 0% | 100% | 60% | 79% | 22% |
| espelhar (não é duplicata) | 0% | 23% | 0% | 0% | 0% |
| **produtos diferentes casados** | 0% | 7,65% | 1,92% | **0,22%** | **0,19%** |

O que eu tiro disso:

- **Use pHash**, com distância de 6 a 8 bits. Ele acha cópias redimensionadas, recomprimidas e com brilho alterado, e raramente confunde produtos diferentes.
- **Use `trim()` quando as margens variam** (a mesma foto com mais ou menos branco em volta, ou levemente recortada). Ele atrapalha com marca d'água e rotação, que mudam o retângulo do conteúdo.
- **A assinatura exata** só serve para arquivos idênticos. Fica para compatibilidade com dados antigos.
- **Para casar produtos, a foto é um sinal, não uma prova.** No catálogo, a assinatura da imagem era uma das 12 chaves, ao lado de códigos de barras e nomes.

Os números vêm de fotos sintéticas; fotos reais têm textura e sombra. Rode o teste nas suas imagens antes de escolher um limite.

## Como o pHash funciona

<p align="center"><img src="docs/img/phash-steps.pt-BR.png" alt="Passos do pHash: foto, 32x32 em cinza, 8x8 frequências mais baixas da DCT, bits acima da mediana" width="900"></p>

A imagem é reduzida a 32×32 em cinza com média exata por área. Uma transformada discreta do cosseno separa as formas gerais dos detalhes, e só as 8×8 frequências mais baixas ficam. Cada uma vira um bit: 1 se estiver acima da mediana delas. Redimensionar e comprimir mudam os detalhes, não a forma geral, então os bits quase não mudam. Todos os passos usam inteiros, inclusive a DCT, a partir de uma tabela de cossenos arredondada. A especificação completa, a mesma que as duas implementações seguem, está em [spec/ALGORITHMS.md](spec/ALGORITHMS.md).

## O que tem

| | Python (`similar_image_finder`) | .NET (`SimilarImageFinder`) |
|---|---|---|
| Carregar imagem (orientação EXIF, transparência sobre branco) | `load_gray(caminho_ou_bytes)` | `ImageLoader.Load(caminho)` (SkiaSharp) ou `GrayImage.FromRgba(...)` |
| Remover borda uniforme | `imagem.trim()` | `imagem.Trim()` |
| Hashes (qualquer tamanho: 8 = 64 bits, 16 = 256 bits) | `average_hash`, `difference_hash`, `perceptual_hash` | `ImageHasher.AverageHash`, `DifferenceHash`, `PerceptualHash` |
| Assinatura exata, formato de 2019 | `exact_signature`, `legacy_decimal` | `ImageHasher.ExactSignature`, `LegacyDecimal` |
| Comparar duas imagens diretamente | `percentage_difference`, `bhattacharyya_distance` | `Similarity.PercentageDifference`, `BhattacharyyaDistance` |
| Buscar até uma distância | `HashIndex(max_distance).query(h)` | `new HashIndex<TKey>(maxDistance).Query(h)` |
| Agrupar quase duplicadas | `find_duplicates(itens, max_distance)` | `ImageGroups.FindDuplicates(itens, maxDistance)` |
| Achar imagens genéricas e logos | `find_generic(itens, min_owners=100)` | `ImageGroups.FindGeneric(itens, minOwners)` |
| Linha de comando | `similar-image-finder hash / dupes` | [`samples/FindDuplicates`](dotnet/samples/FindDuplicates) |

O núcleo .NET **não tem dependências** e trabalha com pixels decodificados; o `SimilarImageFinder.SkiaSharp` acrescenta a leitura de arquivos.

### Milhões de imagens

Comparar cada hash com todos os outros não escala. O `HashIndex` usa **multi-index hashing**: os 64 bits são cortados em quatro faixas de 16 bits, e se dois hashes estão a até 6 bits, pelo menos uma faixa está a até 1 bit. A busca consulta cada faixa e as suas 16 variações de um bit, e confere só esses candidatos. A busca é exata: nada dentro da distância fica de fora.

Com 1.050.000 hashes aleatórios de 64 bits e distância 6, numa VM de nuvem com 2 núcleos:

| | .NET | Python |
|---|---:|---:|
| inserir todos os hashes | 5 s | 7 s |
| uma busca | 0,4 ms | 0,6 ms |
| agrupar tudo | 3 min | 9 min |
| pHash de uma imagem 1200×1200 (já decodificada) | 5 ms | 17 ms |

### Imagens genéricas e logos

```python
from similar_image_finder import find_generic, exact_signature

genericas = find_generic(((id_produto, exact_signature(caminho)) for id_produto, caminho in fotos), min_owners=100)
```

No catálogo, uma assinatura presente em mais de 100 produtos era quase sempre um "sem foto" ou o logo de uma loja. Essas imagens deixaram de ligar produtos; sem isso, todo produto sem foto de uma loja seria "o mesmo produto".

## Os mesmos resultados em Python e .NET

O `tools/make_testdata.py` gera o [`testdata/golden.json`](testdata/golden.json) a partir da implementação em Python: níveis de cinza, grades reduzidas, as oito orientações EXIF, todos os hashes, recortes e comparações, para 10 imagens PNG e 8 matrizes de pixels. Os testes .NET precisam reproduzir tudo exatamente, e o CI roda os dois. A única exceção é o JPEG: decodificadores diferentes podem divergir em um nível de cinza em alguns pixels, então hashes de JPEG podem diferir em um ou dois bits entre as linguagens.

## Instalação

Python 3.10+:

```bash
pip install "git+https://github.com/CaiqueDourado/SimilarImageFinder#subdirectory=python"
```

.NET 8:

```bash
git clone https://github.com/CaiqueDourado/SimilarImageFinder.git
dotnet add reference SimilarImageFinder/dotnet/src/SimilarImageFinder.SkiaSharp/SimilarImageFinder.SkiaSharp.csproj
```

No Linux, acrescente também o `SkiaSharp.NativeAssets.Linux.NoDependencies`. As releases trazem o `.nupkg` e o wheel do Python.

## Repositório

```
python/        pacote, testes e linha de comando
dotnet/        núcleo (sem dependências), leitor SkiaSharp, testes, exemplo
spec/          ALGORITHMS.md: a especificação que as duas seguem
testdata/      imagens e golden.json usados pelos dois conjuntos de testes
evaluation/    o teste comparativo acima (evaluate.py, figures.py, resultados)
tools/         fotos sintéticas de produto e gerador dos dados de teste
```

## Créditos

- O pHash segue o método da DCT descrito por Christoph Zauner (*Implementation and Benchmarking of Perceptual Image Hash Functions*, 2010) e por Neal Krawetz em "Looks Like It" (2011).
- A busca segue Norouzi, Punjani e Fleet, *Fast Search in Hamming Space with Multi-Index Hashing* (CVPR 2012).
- As comparações por porcentagem e Bhattacharyya foram popularizadas pelo ImageComparison de Jakob Krarup (xnafan.net, 2012), usado no pipeline de 2019. Esta é uma implementação independente; veja [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

## Licença

MIT. Por [Caique Dourado](https://github.com/CaiqueDourado).
