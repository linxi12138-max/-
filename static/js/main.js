document.addEventListener('submit',e=>{if(e.target.matches('[data-confirm]')&&!confirm('确定删除？'))e.preventDefault()});
