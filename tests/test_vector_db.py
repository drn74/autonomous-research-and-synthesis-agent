import asyncio
from database.vector_manager import VectorManager
from core.config import console

async def test_vector_db():
    try:
        console.print("[bold blue]Testing VectorManager initialization...[/bold blue]")
        vm = VectorManager(collection_name="test_collection")
        
        test_chunks = ["This is a test chunk about AI.", "ARSA is an autonomous research agent."]
        test_metadatas = [{"type": "test"}, {"type": "test"}]
        
        vm.add_chunks(session_id="test_sess", url="http://test.com", chunks=test_chunks, metadatas=test_metadatas)
        
        console.print("[bold yellow]Querying Vector DB...[/bold yellow]")
        results = vm.query(session_id="test_sess", query_text="What is ARSA?")
        
        for i, res in enumerate(results):
            console.print(f"Result {i+1}: {res.page_content} (Source: {res.metadata.get('source_url')})")
            
        console.print("[bold green]VectorManager test passed![/bold green]")
    except Exception as e:
        console.print(f"[bold red]VectorManager test failed: {e}[/bold red]")

if __name__ == "__main__":
    asyncio.run(test_vector_db())
