/** Print only the selected reception service; never recovery links or staff activity. */
export function printService(serviceId:number,mode:'qr'|'token'){
  document.querySelectorAll('.reception-card').forEach(card=>card.classList.toggle('print-target',card.getAttribute('data-service')===String(serviceId)));
  document.body.dataset.printMode=mode;
  window.addEventListener('afterprint',()=>{delete document.body.dataset.printMode;document.querySelectorAll('.print-target').forEach(card=>card.classList.remove('print-target'));},{once:true});
  window.print();
}
