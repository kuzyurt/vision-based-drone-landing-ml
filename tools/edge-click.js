(() => { const button=document.querySelector('.fs-go'); if(!button)return 'no start button'; button.click(); return {clicked:true,disabled:button.disabled}; })()
